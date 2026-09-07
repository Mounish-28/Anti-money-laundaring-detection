import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
try:
    import catboost
except ImportError:
    pass

import pandas as pd
import numpy as np
import joblib
import json
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.data import Data
from torch_geometric.nn import GCNConv
import networkx as nx
import lightgbm as lgb
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score, average_precision_score
from utils import set_seed, cleanup_memory, optimize_threshold_v4

class GCN(torch.nn.Module):
    def __init__(self, in_channels):
        super(GCN, self).__init__()
        self.conv1 = GCNConv(in_channels, 128)
        self.conv2 = GCNConv(128, 64)
        self.dropout = nn.Dropout(0.25)
        self.classifier = nn.Linear(64, 1)

    def forward(self, x, edge_index):
        x = self.conv1(x, edge_index)
        x = F.relu(x)
        x = self.dropout(x)
        x = self.conv2(x, edge_index)
        x = F.relu(x)
        return self.classifier(x)
        
    def get_embeddings(self, x, edge_index):
        x = self.conv1(x, edge_index)
        x = F.relu(x)
        x = self.dropout(x)
        x = self.conv2(x, edge_index)
        x = F.relu(x)
        return x

def run_pipeline():
    print("=== DATASET 4: IBM AMLSIM (GCN + LIGHTGBM) - PHASE 1.7 ===")
    set_seed(42)
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    
    # Load data
    accounts_path = "../IBM AMlSim/accounts.csv" if os.path.exists("../IBM AMlSim/accounts.csv") else "IBM AMlSim/accounts.csv"
    tx_path = "../IBM AMlSim/transactions.csv" if os.path.exists("../IBM AMlSim/transactions.csv") else "IBM AMlSim/transactions.csv"
    alerts_path = "../IBM AMlSim/alerts.csv" if os.path.exists("../IBM AMlSim/alerts.csv") else "IBM AMlSim/alerts.csv"
    
    print("Loading data...")
    accounts_df = pd.read_csv(accounts_path)
    transactions_df = pd.read_csv(tx_path)
    alerts_df = pd.read_csv(alerts_path)
    
    # Target label: accounts in alerts are '1', else '0'
    suspicious_accounts = set(alerts_df['ACCOUNT_ID'].unique() if 'ACCOUNT_ID' in alerts_df.columns else alerts_df.iloc[:, 0].unique())
    accounts_df['Is Laundering'] = accounts_df['ACCOUNT_ID'].apply(lambda x: 1 if x in suspicious_accounts else 0)
    
    # Create account index mapping
    account_mapping = {acc: i for i, acc in enumerate(accounts_df['ACCOUNT_ID'])}
    
    # Build Graph Features using NetworkX
    print("Building Graph & Computing NetworkX Metrics...")
    G = nx.from_pandas_edgelist(transactions_df, 'SENDER_ACCOUNT_ID', 'RECEIVER_ACCOUNT_ID', create_using=nx.DiGraph())
    
    in_degree = dict(G.in_degree())
    out_degree = dict(G.out_degree())
    pagerank = nx.pagerank(G, alpha=0.85)
    
    accounts_df['in_degree'] = accounts_df['ACCOUNT_ID'].map(in_degree).fillna(0)
    accounts_df['out_degree'] = accounts_df['ACCOUNT_ID'].map(out_degree).fillna(0)
    accounts_df['degree_ratio'] = accounts_df['in_degree'] / (accounts_df['out_degree'] + 1e-5)
    accounts_df['pagerank'] = accounts_df['ACCOUNT_ID'].map(pagerank).fillna(0)
    
    # Prepare edges for PyG
    valid_edges = transactions_df[
        transactions_df['SENDER_ACCOUNT_ID'].isin(account_mapping) &
        transactions_df['RECEIVER_ACCOUNT_ID'].isin(account_mapping)
    ]
    edge_index = torch.tensor([
        valid_edges['SENDER_ACCOUNT_ID'].map(account_mapping).values,
        valid_edges['RECEIVER_ACCOUNT_ID'].map(account_mapping).values
    ], dtype=torch.long)
    
    # Features and labels
    feature_cols = [c for c in accounts_df.columns if c not in ['ACCOUNT_ID', 'Is Laundering']]
    for c in feature_cols:
        accounts_df[c] = pd.to_numeric(accounts_df[c], errors='coerce').fillna(0)
    
    x = torch.tensor(accounts_df[feature_cols].values.astype(np.float32), dtype=torch.float)
    y = torch.tensor(accounts_df['Is Laundering'].values, dtype=torch.float)
    
    # Split Strategy: connected components to prevent edge-target leakage
    print("Computing connected components for split...")
    undirected_G = G.to_undirected()
    components = list(nx.connected_components(undirected_G))
    
    np.random.seed(42)
    np.random.shuffle(components)
    
    train_nodes, val_nodes, test_nodes = set(), set(), set()
    n_nodes = len(accounts_df)
    
    max_comp_size = max([len(c) for c in components]) if components else 0
    if max_comp_size > 0.5 * n_nodes:
        print("Graph is mostly one component. Using random node split.")
        nodes = list(accounts_df['ACCOUNT_ID'])
        np.random.shuffle(nodes)
        train_nodes = set(nodes[:int(0.7 * n_nodes)])
        val_nodes = set(nodes[int(0.7 * n_nodes):int(0.85 * n_nodes)])
        test_nodes = set(nodes[int(0.85 * n_nodes):])
    else:
        for comp in components:
            if len(train_nodes) < 0.7 * n_nodes:
                train_nodes.update(comp)
            elif len(val_nodes) < 0.15 * n_nodes:
                val_nodes.update(comp)
            else:
                test_nodes.update(comp)
                
    if len(val_nodes) == 0:
        nodes = list(accounts_df['ACCOUNT_ID'])
        np.random.shuffle(nodes)
        train_nodes = set(nodes[:int(0.7 * n_nodes)])
        val_nodes = set(nodes[int(0.7 * n_nodes):int(0.85 * n_nodes)])
        test_nodes = set(nodes[int(0.85 * n_nodes):])
            
    train_mask = torch.tensor([acc in train_nodes for acc in accounts_df['ACCOUNT_ID']], dtype=torch.bool)
    val_mask = torch.tensor([acc in val_nodes for acc in accounts_df['ACCOUNT_ID']], dtype=torch.bool)
    test_mask = torch.tensor([acc in test_nodes for acc in accounts_df['ACCOUNT_ID']], dtype=torch.bool)
    
    data = Data(x=x, edge_index=edge_index, y=y)
    data = data.to(device)
    
    print("Training GCN (128 -> 64)...")
    model = GCN(in_channels=x.shape[1]).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=0.01, weight_decay=5e-4)
    criterion = nn.BCEWithLogitsLoss()
    
    best_val_pr = -1
    best_model_state = None
    
    for epoch in range(80):
        model.train()
        optimizer.zero_grad()
        out = model(data.x, data.edge_index)
        loss = criterion(out[train_mask].squeeze(), data.y[train_mask])
        loss.backward()
        optimizer.step()
        
        model.eval()
        with torch.no_grad():
            val_out = model(data.x, data.edge_index)
            val_probs = torch.sigmoid(val_out[val_mask].squeeze()).cpu().numpy()
            try:
                val_pr = average_precision_score(data.y[val_mask].cpu().numpy(), val_probs)
            except ValueError:
                val_pr = 0
            
            if val_pr > best_val_pr:
                best_val_pr = val_pr
                best_model_state = model.state_dict()
                
    model.load_state_dict(best_model_state)
    
    # Extract Embeddings
    print("Extracting GCN embeddings...")
    model.eval()
    with torch.no_grad():
        embeddings = model.get_embeddings(data.x, data.edge_index).cpu().numpy()
        
    X_orig = data.x.cpu().numpy()
    X_concat = np.hstack([X_orig, embeddings])
    y_np = data.y.cpu().numpy()
    
    X_train, y_train = X_concat[train_mask.numpy()], y_np[train_mask.numpy()]
    X_val, y_val = X_concat[val_mask.numpy()], y_np[val_mask.numpy()]
    X_test, y_test = X_concat[test_mask.numpy()], y_np[test_mask.numpy()]
    
    print("Training Downstream LightGBM with balanced weights...")
    lgb_train = lgb.Dataset(X_train, label=y_train)
    lgb_val = lgb.Dataset(X_val, label=y_val, reference=lgb_train)
    
    params = {
        'objective': 'binary',
        'boosting_type': 'gbdt',
        'metric': 'binary_logloss',
        'scale_pos_weight': 10.0,
        'learning_rate': 0.05,
        'num_leaves': 63,
        'max_depth': 6,
        'random_state': 42,
        'verbose': -1
    }
    
    lgb_model = lgb.train(
        params,
        lgb_train,
        num_boost_round=1000,
        valid_sets=[lgb_val],
        callbacks=[lgb.early_stopping(stopping_rounds=50, verbose=False)]
    )
    
    # Validation Threshold Sweep
    print("Tuning threshold on validation set (Phase 1.7 multi-tier sweep)...")
    val_probs = lgb_model.predict(X_val)
    best_t = optimize_threshold_v4(y_val, val_probs, min_acc=0.97, min_rec=0.90)
    print(f"Optimal Threshold T*: {best_t:.4f}")
    
    # Evaluate on untouched Test set
    print("Evaluating on untouched Test set...")
    test_probs = lgb_model.predict(X_test)
    test_preds = (test_probs >= best_t).astype(int)
    
    acc = accuracy_score(y_test, test_preds)
    prec = precision_score(y_test, test_preds, zero_division=0)
    rec = recall_score(y_test, test_preds, zero_division=0)
    f1 = f1_score(y_test, test_preds, zero_division=0)
    roc_auc = roc_auc_score(y_test, test_probs)
    pr_auc = average_precision_score(y_test, test_probs)
    
    metrics = {
        "Dataset": "IBM AMLSim",
        "Architecture": "GCN + Graph Metrics + LGBM",
        "Best_Threshold": float(best_t),
        "Test_Accuracy": float(acc),
        "Precision": float(prec),
        "Recall": float(rec),
        "F1_Score": float(f1),
        "PR_AUC": float(pr_auc),
        "ROC_AUC": float(roc_auc),
        "Target_Met": "YES" if (acc >= 0.97 and (rec >= 0.90 or f1 >= 0.80)) else "PARTIAL"
    }
    print("Dataset 4 Test Results:")
    print(json.dumps(metrics, indent=4))
    
    out_model_dir = "../models/AMLSim" if os.path.exists("../models") else "models/AMLSim"
    out_exp_dir = "../experiments/AMLSim" if os.path.exists("../experiments") else "experiments/AMLSim"
    os.makedirs(out_model_dir, exist_ok=True)
    os.makedirs(out_exp_dir, exist_ok=True)
    
    torch.save(model.state_dict(), os.path.join(out_model_dir, "gcn_v4.pt"))
    torch.save(model.state_dict(), os.path.join(out_model_dir, "gcn_v5.pt"))
    joblib.dump(lgb_model, os.path.join(out_model_dir, "model_v4.joblib"))
    joblib.dump(lgb_model, os.path.join(out_model_dir, "model_v5.joblib"))
    with open(os.path.join(out_exp_dir, "metrics_v4.json"), "w") as f:
        json.dump(metrics, f, indent=4)
    with open(os.path.join(out_exp_dir, "metrics_v5.json"), "w") as f:
        json.dump(metrics, f, indent=4)
        
    print("Dataset 4 Phase 1.9 execution completed successfully (locked benchmark).\n")
    cleanup_memory()

if __name__ == "__main__":
    run_pipeline()
