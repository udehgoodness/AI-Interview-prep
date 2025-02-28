import asyncio
import json
import logging
import os
import uuid
from typing import Dict, Optional, Set

import aiohttp
from aiortc import RTCPeerConnection, RTCSessionDescription, MediaStreamTrack, RTCIceCandidate
from aiortc.contrib.media import MediaBlackhole, MediaPlayer, MediaRecorder

logger = logging.getLogger("webrtc")

# Store active peer connections
peer_connections: Dict[str, RTCPeerConnection] = {}
# Store connected users
connected_users: Set[str] = set()

class WebRTCService:
    """
    Service for handling WebRTC connections
    """
    
    @staticmethod
    async def create_peer_connection(session_id: str) -> RTCPeerConnection:
        """
        Create a new peer connection for a session
        
        Args:
            session_id: Unique session identifier
            
        Returns:
            RTCPeerConnection object
        """
        pc = RTCPeerConnection()
        
        # Store the peer connection
        peer_connections[session_id] = pc
        
        @pc.on("iceconnectionstatechange")
        async def on_iceconnectionstatechange():
            logger.info(f"ICE connection state for {session_id}: {pc.iceConnectionState}")
            if pc.iceConnectionState == "failed" or pc.iceConnectionState == "closed":
                await WebRTCService.close_peer_connection(session_id)
        
        @pc.on("track")
        def on_track(track):
            logger.info(f"Track received from {session_id}: {track.kind}")
            
            if track.kind == "audio":
                # Handle audio track
                pass
            elif track.kind == "video":
                # Handle video track
                pass
                
            @track.on("ended")
            async def on_ended():
                logger.info(f"Track ended for {session_id}")
        
        return pc
    
    @staticmethod
    async def handle_offer(session_id: str, offer: RTCSessionDescription) -> RTCSessionDescription:
        """
        Handle an incoming WebRTC offer
        
        Args:
            session_id: Unique session identifier
            offer: SDP offer from client
            
        Returns:
            SDP answer to send back to client
        """
        # Create or get peer connection
        if session_id in peer_connections:
            pc = peer_connections[session_id]
        else:
            pc = await WebRTCService.create_peer_connection(session_id)
        
        # Set remote description
        await pc.setRemoteDescription(offer)
        
        # Create answer
        answer = await pc.createAnswer()
        await pc.setLocalDescription(answer)
        
        # Add user to connected users
        connected_users.add(session_id)
        
        return pc.localDescription
    
    @staticmethod
    async def handle_ice_candidate(session_id: str, candidate: dict) -> None:
        """
        Handle an incoming ICE candidate
        
        Args:
            session_id: Unique session identifier
            candidate: ICE candidate from client
        """
        if session_id in peer_connections:
            pc = peer_connections[session_id]
            await pc.addIceCandidate(RTCIceCandidate(
                sdpMid=candidate.get("sdpMid"),
                sdpMLineIndex=candidate.get("sdpMLineIndex"),
                candidate=candidate.get("candidate")
            ))
    
    @staticmethod
    async def close_peer_connection(session_id: str) -> None:
        """
        Close a peer connection
        
        Args:
            session_id: Unique session identifier
        """
        if session_id in peer_connections:
            pc = peer_connections[session_id]
            await pc.close()
            del peer_connections[session_id]
        
        if session_id in connected_users:
            connected_users.remove(session_id)
            
        logger.info(f"Closed peer connection for {session_id}")
    
    @staticmethod
    def get_ice_servers() -> list:
        """
        Get ICE servers configuration
        
        Returns:
            List of ICE server configurations
        """
        # Default to free STUN servers
        ice_servers = [
            {"urls": "stun:stun.l.google.com:19302"},
            {"urls": "stun:stun1.l.google.com:19302"}
        ]
        
        # Add TURN servers if credentials are available
        turn_url = os.getenv("TURN_SERVER_URL")
        turn_username = os.getenv("TURN_SERVER_USERNAME")
        turn_password = os.getenv("TURN_SERVER_PASSWORD")
        
        if turn_url and turn_username and turn_password:
            ice_servers.append({
                "urls": turn_url,
                "username": turn_username,
                "credential": turn_password
            })
            
        return ice_servers
    
    @staticmethod
    def generate_session_id() -> str:
        """
        Generate a unique session ID
        
        Returns:
            Unique session ID string
        """
        return str(uuid.uuid4()) 