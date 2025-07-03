import asyncio
import time

from flare_ai_kit import FlareAIKit
from flare_ai_kit.common import FAssetType


async def main() -> None:
    """
    Comprehensive FAssets operations example - including swaps and redemptions.
    
    This example demonstrates:
    1. Querying supported assets and agent information
    2. Balance and allowance checks  
    3. FAsset swap operations using SparkDEX
    4. Minting and redemption workflows
    
    Note: This example uses placeholder contract addresses. For real usage,
    update the contract addresses in the FAssets connector with actual deployed addresses.
    """
    # Initialize the Flare AI Kit
    kit = FlareAIKit()

    try:
        # Get the FAssets connector
        fassets = await kit.fassets
        
        # Get information about supported FAssets on the current network
        print("=== Supported FAssets ===")
        supported_fassets = await fassets.get_supported_fassets()
        
        for symbol, info in supported_fassets.items():
            print(f"{symbol}: {info.name}")
            print(f"  Underlying: {info.underlying_symbol}")
            print(f"  Decimals: {info.decimals}")
            print(f"  Active: {info.is_active}")
            print(f"  Asset Manager: {info.asset_manager_address}")
            print(f"  FAsset Token: {info.f_asset_address}")
            print()

        # If FXRP is supported, demonstrate comprehensive operations
        if "FXRP" in supported_fassets:
            print("=== FXRP Operations ===")
            
            try:
                # Get FXRP specific information
                fxrp_info = await fassets.get_fasset_info(FAssetType.FXRP)
                print(f"FXRP Info: {fxrp_info}")
                
                # Get asset manager settings
                settings = await fassets.get_asset_manager_settings(FAssetType.FXRP)
                print(f"Asset Manager Settings:")
                print(f"  Asset Name: {settings.get('asset_name')}")
                print(f"  Asset Symbol: {settings.get('asset_symbol')}")
                print(f"  Lot Size: {settings.get('lot_size_amg')}")
                print(f"  Minting Vault CR: {settings.get('minting_vault_collateral_ratio')}")
                print()
                
                # === NEW: Balance and Allowance Operations ===
                print("=== Balance & Allowance Operations ===")
                if fassets.address:
                    try:
                        # Check FXRP balance
                        balance = await fassets.get_fasset_balance(FAssetType.FXRP, fassets.address)
                        print(f"FXRP Balance: {balance} wei")
                        
                        # Check allowance for SparkDEX router (if configured)
                        if fassets.sparkdex_router:
                            allowance = await fassets.get_fasset_allowance(
                                FAssetType.FXRP, 
                                fassets.address, 
                                fassets.sparkdex_router.address
                            )
                            print(f"FXRP Allowance for SparkDEX: {allowance} wei")
                        else:
                            print("SparkDEX router not configured - skipping allowance check")
                    except Exception as e:
                        print(f"Balance/allowance check failed (expected with placeholders): {e}")
                else:
                    print("No account address configured - skipping balance checks")
                print()
                
                # === NEW: Swap Operations ===
                print("=== Swap Operations (SparkDEX Integration) ===")
                try:
                    # Example swap parameters
                    swap_amount = 1000000  # 1 FXRP (6 decimals)
                    min_native_out = 500000000000000000  # 0.5 FLR/SGB  
                    deadline = int(time.time()) + 3600  # 1 hour from now
                    
                    print("1. Swap FXRP for Native Token (FLR/SGB)")
                    tx_hash = await fassets.swap_fasset_for_native(
                        FAssetType.FXRP,
                        amount_in=swap_amount,
                        amount_out_min=min_native_out,
                        deadline=deadline
                    )
                    print(f"   Transaction: {tx_hash}")
                    
                    print("2. Swap Native Token for FXRP")
                    native_amount = 1000000000000000000  # 1 FLR/SGB
                    min_fxrp_out = 900000  # 0.9 FXRP
                    tx_hash = await fassets.swap_native_for_fasset(
                        FAssetType.FXRP,
                        amount_out_min=min_fxrp_out,
                        deadline=deadline,
                        amount_in=native_amount
                    )
                    print(f"   Transaction: {tx_hash}")
                    
                    # Cross-FAsset swap (if multiple FAssets available)
                    if len(supported_fassets) > 1:
                        other_fassets = [k for k in supported_fassets.keys() if k != "FXRP"]
                        if other_fassets:
                            other_fasset = getattr(FAssetType, other_fassets[0])
                            print(f"3. Swap FXRP for {other_fassets[0]}")
                            tx_hash = await fassets.swap_fasset_for_fasset(
                                FAssetType.FXRP,
                                other_fasset,
                                amount_in=swap_amount,
                                amount_out_min=500000,  # Adjust based on decimals
                                deadline=deadline
                            )
                            print(f"   Transaction: {tx_hash}")
                    
                except Exception as e:
                    print(f"Swap operations failed (expected with placeholder addresses): {e}")
                print()
                
                # === Enhanced Minting Workflow ===
                print("=== Complete Minting Workflow ===")
                try:
                    # Get all agents
                    agents = await fassets.get_all_agents(FAssetType.FXRP)
                    print(f"Available Agents: {len(agents)}")
                    
                    if agents:
                        agent_address = agents[0]
                        
                        # Get available lots
                        available_lots = await fassets.get_available_lots(FAssetType.FXRP, agent_address)
                        print(f"Available lots from {agent_address}: {available_lots}")
                        
                        # Step 1: Reserve collateral for minting
                        print("Step 1: Reserve Collateral")
                        reservation_id = await fassets.reserve_collateral(
                            FAssetType.FXRP,
                            agent_vault=agent_address,
                            lots=1,
                            max_minting_fee_bips=100,  # 1%
                            executor=fassets.address or "0x0000000000000000000000000000000000000000",
                            executor_fee_nat=0
                        )
                        print(f"Collateral Reservation ID: {reservation_id}")
                        
                        # Step 2: Execute minting (after underlying payment)
                        print("Step 2: Execute Minting")
                        payment_reference = "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
                        minted_amount = await fassets.execute_minting(
                            FAssetType.FXRP,
                            collateral_reservation_id=reservation_id,
                            payment_reference=payment_reference,
                            recipient=fassets.address or "0x0000000000000000000000000000000000000000"
                        )
                        print(f"Minted Amount: {minted_amount} wei")
                        
                except Exception as e:
                    print(f"Minting workflow failed (expected with placeholder addresses): {e}")
                print()
                
                # === Redemption Operations ===  
                print("=== Redemption Operations ===")
                try:
                    # Redeem FAssets back to underlying
                    redemption_id = await fassets.redeem_from_agent(
                        FAssetType.FXRP,
                        lots=1,
                        max_redemption_fee_bips=100,  # 1%
                        underlying_address="rXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",  # XRP address
                        executor=fassets.address or "0x0000000000000000000000000000000000000000",
                        executor_fee_nat=0
                    )
                    print(f"Redemption Request ID: {redemption_id}")
                    
                    # Get redemption request details
                    if redemption_id > 0:
                        redemption_details = await fassets.get_redemption_request(FAssetType.FXRP, redemption_id)
                        print(f"Redemption Details:")
                        print(f"  Agent Vault: {redemption_details.get('agent_vault')}")
                        print(f"  Value UBA: {redemption_details.get('value_uba')}")
                        print(f"  Fee UBA: {redemption_details.get('fee_uba')}")
                        print(f"  Payment Address: {redemption_details.get('payment_address')}")
                        
                except Exception as e:
                    print(f"Redemption operations failed (expected with placeholder addresses): {e}")
                print()
                        
            except Exception as e:
                print(f"Error with FXRP operations (expected with placeholder addresses): {e}")
        
        # Check for FBTC on Flare Mainnet
        if "FBTC" in supported_fassets:
            print("=== FBTC Operations ===")
            try:
                fbtc_info = await fassets.get_fasset_info(FAssetType.FBTC)
                print(f"FBTC Info: {fbtc_info}")
                print(f"Status: {'Coming Soon' if not fbtc_info.is_active else 'Active'}")
            except Exception as e:
                print(f"Error with FBTC operations: {e}")
            print()
        
        # Check for FDOGE on Flare Mainnet  
        if "FDOGE" in supported_fassets:
            print("=== FDOGE Operations ===")
            try:
                fdoge_info = await fassets.get_fasset_info(FAssetType.FDOGE)
                print(f"FDOGE Info: {fdoge_info}")
                print(f"Status: {'Coming Soon' if not fdoge_info.is_active else 'Active'}")
            except Exception as e:
                print(f"Error with FDOGE operations: {e}")
            print()
                
    except Exception as e:
        print(f"Error initializing FAssets: {e}")
        print("This is expected if running with placeholder contract addresses.")
        print("Update the contract addresses in the FAssets connector for real usage.")


async def demonstrate_minting_flow():
    """
    Demonstrate the FAssets minting flow (educational purposes).
    
    Note: This requires real contract addresses and sufficient collateral.
    """
    print("\n=== FAssets Minting Flow (Educational) ===")
    
    # Initialize the Flare AI Kit
    kit = FlareAIKit()
    
    try:
        fassets = await kit.fassets
        
        print("Step 1: Reserve collateral")
        print("- Call reserve_collateral() with agent, lots, and fees")
        print("- This locks collateral and provides a reservation ID")
        
        print("\nStep 2: Send underlying asset payment")
        print("- Send XRP/BTC/DOGE to the agent's underlying address")
        print("- Include the payment reference from the reservation")
        
        print("\nStep 3: Execute minting")
        print("- Call executeMinting() with reservation ID and payment proof")
        print("- FAssets are minted to your address")
        
        print("\nStep 4: Monitor the process")
        print("- Use get_collateral_reservation_data() to check status")
        print("- FDC attestations verify the underlying payment")
        
        print("\nFor redemption:")
        print("- Call redeem_from_agent() to burn FAssets")
        print("- Agent sends underlying assets to your address")
        print("- Use get_redemption_request() to monitor status")
        
    except Exception as e:
        print(f"Demo setup error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
    asyncio.run(demonstrate_minting_flow()) 