class CyloClient:
    """
    Client for interacting with the Cylo protocol.
    """

    def __init__(self):
        self.name = "Cylo"

    def describe_cylo_services(self) -> str:
        return """
        Cylo is a decentralized protocol on the Flare Network,
        enabling users to create and manage synthetic assets.
        It allows for the creation of synthetic assets that track the value of real-world assets,
        providing a bridge between traditional finance and decentralized finance (DeFi).
        Cylo leverages the Flare Time Series Oracle (FTSOv2) for accurate price feeds,
        ensuring that synthetic assets are always pegged to their underlying assets.
        """
