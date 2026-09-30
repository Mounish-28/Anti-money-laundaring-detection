"""
app/surveillance/connection_manager.py
=============================================================================
QuantumAML Nexus -- Decoupled Surveillance WebSocket Broadcast Manager
Lead Infrastructure Engineer Component:
Manages dedicated, isolated WebSocket client pools for decoupled financial
streams:
  1. Banking Switch Stream (/ws/surveillance/banking): UPI and banking events.
  2. Cryptocurrency Stream (/ws/surveillance/crypto): Mempool & blockchain events.
  3. Unified Stream (/ws/surveillance/unified): Merged multi-rail war-room feed.
=============================================================================
"""

from __future__ import annotations
import asyncio
import json
import logging
from typing import Any, Dict, List, Set

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger("SurveillanceConnectionManager")


class SurveillanceConnectionManager:
    """
    Thread-safe, decoupled asynchronous WebSocket connection manager.
    Enforces strict channel isolation so banking subscribers do not receive
    crypto noise and crypto analysts do not receive retail banking events.
    """

    def __init__(self):
        self.channels: Dict[str, Set[WebSocket]] = {
            "banking": set(),
            "crypto": set(),
            "unified": set(),
        }
        self._lock = asyncio.Lock()
        self.total_broadcasts = 0

    async def connect(self, websocket: WebSocket, channel: str):
        """Accepts WebSocket connection and assigns to requested decoupled pool."""
        await websocket.accept()
        async with self._lock:
            if channel not in self.channels:
                self.channels[channel] = set()
            self.channels[channel].add(websocket)

        logger.info(
            f"Surveillance client connected to channel [{channel}]. Active pool size: {len(self.channels[channel])}"
        )

    async def disconnect(self, websocket: WebSocket, channel: str):
        """Safely unregisters a socket upon disconnect or connection termination."""
        async with self._lock:
            if channel in self.channels and websocket in self.channels[channel]:
                self.channels[channel].remove(websocket)
                logger.info(
                    f"Surveillance client disconnected from [{channel}]. Remaining: {len(self.channels[channel])}"
                )

    async def _safe_send_json(self, websocket: WebSocket, payload: Dict[str, Any]) -> bool:
        """Sends JSON to an individual socket with graceful failure handling."""
        try:
            await websocket.send_json(payload)
            return True
        except Exception:
            return False

    async def broadcast_banking(self, envelope_dict: Dict[str, Any]) -> int:
        """
        Dispatches banking / UPI event exclusively to 'banking' and 'unified' subscribers.
        Returns total number of recipients reached.
        """
        self.total_broadcasts += 1
        recipients: List[WebSocket] = []
        async with self._lock:
            recipients.extend(list(self.channels.get("banking", set())))
            recipients.extend(list(self.channels.get("unified", set())))

        if not recipients:
            return 0

        dead_sockets: List[WebSocket] = []
        sent_count = 0

        for ws in recipients:
            success = await self._safe_send_json(ws, envelope_dict)
            if success:
                sent_count += 1
            else:
                dead_sockets.append(ws)

        # Cleanup any dead sockets
        if dead_sockets:
            async with self._lock:
                for ws in dead_sockets:
                    self.channels["banking"].discard(ws)
                    self.channels["unified"].discard(ws)

        return sent_count

    async def broadcast_crypto(self, envelope_dict: Dict[str, Any]) -> int:
        """
        Dispatches cryptocurrency event exclusively to 'crypto' and 'unified' subscribers.
        Returns total number of recipients reached.
        """
        self.total_broadcasts += 1
        recipients: List[WebSocket] = []
        async with self._lock:
            recipients.extend(list(self.channels.get("crypto", set())))
            recipients.extend(list(self.channels.get("unified", set())))

        if not recipients:
            return 0

        dead_sockets: List[WebSocket] = []
        sent_count = 0

        for ws in recipients:
            success = await self._safe_send_json(ws, envelope_dict)
            if success:
                sent_count += 1
            else:
                dead_sockets.append(ws)

        # Cleanup any dead sockets
        if dead_sockets:
            async with self._lock:
                for ws in dead_sockets:
                    self.channels["crypto"].discard(ws)
                    self.channels["unified"].discard(ws)

        return sent_count

    def get_subscriber_counts(self) -> Dict[str, int]:
        """Returns active socket counts across all decoupled channels."""
        banking_count = len(self.channels.get("banking", set()))
        crypto_count = len(self.channels.get("crypto", set()))
        unified_count = len(self.channels.get("unified", set()))
        total = sum(len(pool) for pool in self.channels.values())
        return {
            "banking": banking_count,
            "crypto": crypto_count,
            "unified": unified_count,
            "total": total,
            "banking_channel": banking_count,
            "crypto_channel": crypto_count,
            "unified_channel": unified_count,
            "total_active_subscribers": total,
        }


# Global singleton connection manager
surveillance_manager = SurveillanceConnectionManager()
