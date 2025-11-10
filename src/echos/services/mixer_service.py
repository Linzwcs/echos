from typing import Optional
from ..agent.tools import tool
from ..interfaces import IDAWManager
from ..models import ToolResponse


class IMixerService:
    """Interface for mixer operations"""
    pass


class MixerService(IMixerService):
    """
    Service for controlling mixer operations like volume, pan, mute, solo, and sends.
    """

    def __init__(self, manager: IDAWManager):
        self._manager = manager

    @tool(category="mixer",
          description="Set track volume in dB",
          returns="Updated volume value",
          examples=[
              "set_volume(project_id='...', track_id='...', volume_db=-6.0)",
              "set_volume(project_id='...', track_id='...', volume_db=0.0)"
          ])
    def set_volume(self, project_id: str, track_id: str,
                   volume_db: float) -> ToolResponse:
        """
        Set the volume of a track in decibels.
        
        Args:
            project_id: ID of the project
            track_id: ID of the track
            volume_db: Volume in dB (-100.0 to +12.0)
            
        Returns:
            Success response with updated volume
        """
        project = self._manager.get_project(project_id)
        if not project:
            return ToolResponse("error", None,
                                f"Project '{project_id}' not found.")

        track = project.router.nodes.get(track_id)
        if not track or not hasattr(track, 'mixer_channel'):
            return ToolResponse(
                "error", None,
                f"Track '{track_id}' not found or has no mixer.")

        # Clamp volume to valid range
        volume_db = max(-100.0, min(12.0, volume_db))

        track.mixer_channel.volume.set_value(volume_db, immediate=True)

        return ToolResponse("success", {
            "track_id": track_id,
            "volume_db": volume_db
        }, f"Volume set to {volume_db:.1f} dB")

    @tool(
        category="mixer",
        description="Set track pan position",
        returns="Updated pan value",
        examples=[
            "set_pan(project_id='...', track_id='...', pan=0.0)",  # Center
            "set_pan(project_id='...', track_id='...', pan=-1.0)",  # Full left
            "set_pan(project_id='...', track_id='...', pan=1.0)"  # Full right
        ])
    def set_pan(self, project_id: str, track_id: str,
                pan: float) -> ToolResponse:
        """
        Set the pan position of a track.
        
        Args:
            project_id: ID of the project
            track_id: ID of the track
            pan: Pan position (-1.0 = full left, 0.0 = center, 1.0 = full right)
            
        Returns:
            Success response with updated pan
        """
        project = self._manager.get_project(project_id)
        if not project:
            return ToolResponse("error", None,
                                f"Project '{project_id}' not found.")

        track = project.router.nodes.get(track_id)
        if not track or not hasattr(track, 'mixer_channel'):
            return ToolResponse(
                "error", None,
                f"Track '{track_id}' not found or has no mixer.")

        # Clamp pan to valid range
        pan = max(-1.0, min(1.0, pan))

        track.mixer_channel.pan.set_value(pan, immediate=True)

        return ToolResponse("success", {
            "track_id": track_id,
            "pan": pan
        }, f"Pan set to {pan:.2f}")

    @tool(category="mixer",
          description="Mute or unmute a track",
          returns="Updated mute state",
          examples=[
              "set_mute(project_id='...', track_id='...', muted=True)",
              "set_mute(project_id='...', track_id='...', muted=False)"
          ])
    def set_mute(self, project_id: str, track_id: str,
                 muted: bool) -> ToolResponse:
        """
        Mute or unmute a track.
        
        Args:
            project_id: ID of the project
            track_id: ID of the track
            muted: True to mute, False to unmute
            
        Returns:
            Success response with mute state
        """
        project = self._manager.get_project(project_id)
        if not project:
            return ToolResponse("error", None,
                                f"Project '{project_id}' not found.")

        track = project.router.nodes.get(track_id)
        if not track or not hasattr(track, 'mixer_channel'):
            return ToolResponse(
                "error", None,
                f"Track '{track_id}' not found or has no mixer.")

        track.mixer_channel.is_muted = muted

        return ToolResponse("success", {
            "track_id": track_id,
            "muted": muted
        }, f"Track {'muted' if muted else 'unmuted'}")

    @tool(category="mixer",
          description="Solo or unsolo a track",
          returns="Updated solo state")
    def set_solo(self, project_id: str, track_id: str,
                 soloed: bool) -> ToolResponse:
        """
        Solo or unsolo a track.
        
        Args:
            project_id: ID of the project
            track_id: ID of the track
            soloed: True to solo, False to unsolo
            
        Returns:
            Success response with solo state
        """
        project = self._manager.get_project(project_id)
        if not project:
            return ToolResponse("error", None,
                                f"Project '{project_id}' not found.")

        track = project.router.nodes.get(track_id)
        if not track or not hasattr(track, 'mixer_channel'):
            return ToolResponse(
                "error", None,
                f"Track '{track_id}' not found or has no mixer.")

        track.mixer_channel.is_solo = soloed

        return ToolResponse("success", {
            "track_id": track_id,
            "soloed": soloed
        }, f"Track {'soloed' if soloed else 'unsoloed'}")

    @tool(category="mixer",
          description="Get mixer state for a track",
          returns="Complete mixer state including volume, pan, mute, solo")
    def get_mixer_state(self, project_id: str, track_id: str) -> ToolResponse:
        """
        Get the complete mixer state for a track.
        
        Args:
            project_id: ID of the project
            track_id: ID of the track
            
        Returns:
            Mixer state including all parameters
        """
        project = self._manager.get_project(project_id)
        if not project:
            return ToolResponse("error", None,
                                f"Project '{project_id}' not found.")

        track = project.router.nodes.get(track_id)
        if not track or not hasattr(track, 'mixer_channel'):
            return ToolResponse(
                "error", None,
                f"Track '{track_id}' not found or has no mixer.")

        mixer = track.mixer_channel
        state = {
            "track_id":
            track_id,
            "track_name":
            track.name,
            "volume_db":
            mixer.volume.value,
            "pan":
            mixer.pan.value,
            "muted":
            mixer.is_muted,
            "soloed":
            mixer.is_solo,
            "inserts": [{
                "plugin_id": p.plugin_instance_id,
                "plugin_name": p.descriptor.name,
                "enabled": p.is_enabled
            } for p in mixer.inserts],
            "sends": [{
                "send_id": s.send_id,
                "target": s.target_bus_node_id,
                "level_db": s.level.value,
                "post_fader": s.is_post_fader,
                "enabled": s.is_enabled
            } for s in mixer.sends]
        }

        return ToolResponse("success", state,
                            f"Mixer state for '{track.name}' retrieved")

    @tool(category="mixer",
          description="Set input gain for a track",
          returns="Updated input gain value")
    def set_input_gain(self, project_id: str, track_id: str,
                       gain_db: float) -> ToolResponse:
        """
        Set the input gain of a track.
        
        Args:
            project_id: ID of the project
            track_id: ID of the track
            gain_db: Input gain in dB
            
        Returns:
            Success response with updated gain
        """
        project = self._manager.get_project(project_id)
        if not project:
            return ToolResponse("error", None,
                                f"Project '{project_id}' not found.")

        track = project.router.nodes.get(track_id)
        if not track or not hasattr(track, 'mixer_channel'):
            return ToolResponse(
                "error", None,
                f"Track '{track_id}' not found or has no mixer.")

        gain_db = max(-100.0, min(12.0, gain_db))
        track.mixer_channel._input_gain.set_value(gain_db, immediate=True)

        return ToolResponse("success", {
            "track_id": track_id,
            "input_gain_db": gain_db
        }, f"Input gain set to {gain_db:.1f} dB")
