import logging
from typing import Any, Dict

import socketio

from era_5g_interface.channels import DATA_ERROR_EVENT, DATA_NAMESPACE, CallbackInfoClient, Channels, ChannelType

logger = logging.getLogger(__name__)


class ClientChannels(Channels):
    """Channels class is used to define channel data callbacks and contains send functions.

    It handles image frames JPEG and H.264 encoding/decoding. Data is sent via the DATA_NAMESPACE.
    """

    _callbacks_info: Dict[str, CallbackInfoClient]

    def __init__(self, sio: socketio.Client, callbacks_info: Dict[str, CallbackInfoClient], **kwargs):
        """Constructor.

        Args:
            sio (socketio.Client): Socketio Client object.
            callbacks_info (Dict[str, CallbackInfoClient]): Callbacks Info dictionary, key is custom event name.
            back_pressure_size (int, optional): Back pressure size - max size of eio.queue.qsize().
            recreate_h264_attempts_count (int): How many times try to recreate the H.264 encoder/decoder.
            stats (bool): Store output data sizes.
        """

        super().__init__(sio, callbacks_info, **kwargs)

        self._sio.on(DATA_ERROR_EVENT, lambda data: self.data_error_callback(data), namespace=DATA_NAMESPACE)

        for event, callback_info in self._callbacks_info.items():
            logger.info(f"Creating client channels callback, type: {callback_info.type}, event: '{event}'")
            if callback_info.type is ChannelType.JSON:
                self._sio.on(
                    event,
                    lambda data, local_event=event: self.json_callback(data, local_event),
                    namespace=DATA_NAMESPACE,
                )
            elif callback_info.type is ChannelType.JSON_LZ4:
                self._sio.on(
                    event,
                    lambda sid, data, local_event=event: self.json_lz4_callback(data, local_event),
                    namespace=DATA_NAMESPACE,
                )
            elif callback_info.type in (ChannelType.JPEG, ChannelType.H264):
                self._sio.on(
                    event,
                    lambda data, local_event=event: self.image_callback(data, local_event),
                    namespace=DATA_NAMESPACE,
                )
            else:
                raise ValueError(f"Unknown channel type: {callback_info.type}")

    def json_callback(self, data: Dict[str, Any], event: str) -> None:
        """Allows to receive general JSON data on DATA_NAMESPACE.

        Args:
            data (Dict[str, Any]): JSON data.
            event (str): Event name.
        """

        self._callbacks_info[event].callback(data)

    def json_lz4_callback(self, data: bytes, event: str) -> None:
        """Allows to receive LZ4 compressed general JSON data on DATA_NAMESPACE.

        Args:
            data (bytes): LZ4 compressed JSON data.
            event (str): Event name.
        """

        decoded_data = super().data_lz4_decode(data, event)
        if decoded_data:
            self.json_callback(decoded_data, event)

    def image_callback(self, data: Dict[str, Any], event: str) -> None:
        """Allows to receive JPEG or H.264 encoded image on DATA_NAMESPACE.

        Args:
            data (Dict[str, Any]): Received dictionary with frame data.
            event (str): Event name.
        """

        decoded_data = super().image_decode(data, event)
        if decoded_data:
            self._callbacks_info[event].callback(decoded_data)
