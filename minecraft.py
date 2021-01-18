import requests

import mojang

class PlayerSkin(mojang.Player):
    def get_full(self):
        url = f'https://visage.surgeplay.com/full/256/{self.uuid}'
        return url
    
    def get_download(self):
        url = f'https://visage.surgeplay.com/skin/512/{self.uuid}'
        return url

