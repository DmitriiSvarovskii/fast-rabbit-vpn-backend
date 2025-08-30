from .base import BaseConfig


class VPNSettings(BaseConfig):
    PBK: str
    SID: str
    SNI: str
    DOMAIN: str
    FLOW: str


vpn_settings = VPNSettings()
