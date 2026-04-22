import json
from channels.generic.websocket import AsyncWebsocketConsumer
import re

class StatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.username = self.scope['url_route']['kwargs']['username']
        self.safe_name = re.sub(r'[^a-zA-Z0-9._-]', '_', self.username)
        self.group_name = f"stats_{self.safe_name}"

        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )

    async def stat_update(self, event):
        stats = event['stats']
        await self.send(text_data=json.dumps({
            'stats': stats
        }))