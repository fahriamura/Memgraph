"""
Add missing games and points data to graph
"""

from memgraph_handler import MemgraphHandler
from datetime import datetime

handler = MemgraphHandler("localhost", 7687)

if handler.connect():
    print("\n" + "="*70)
    print("ADDING MISSING DATA")
    print("="*70)
    
    # Add Games
    print("\n[1] Adding games...")
    
    games_data = [
        ("Testnet", "NetworkState", "hosts_game", "Snake", "Game"),
        ("Testnet", "NetworkState", "hosts_game", "Spritetype", "Game"),
        ("Snake", "Game", "tracked_by", "Irys Games Checker", "Tool"),
        ("Spritetype", "Game", "tracked_by", "Irys Games Checker", "Tool"),
    ]
    
    for subj, subj_type, rel, obj, obj_type in games_data:
        handler.insert_triplet(
            subject=subj,
            subject_type=subj_type,
            relation=rel,
            obj=obj,
            obj_type=obj_type,
            source="manual_fix"
        )
    
    # Add Points/Rank data
    print("\n[2] Adding points/rank data...")
    
    points_data = [
        ("QuestLand", "Feature", "rewards_points_on", "Galxe", "Platform"),
        ("Rank", "Metric", "displayed_on", "Galxe", "Platform"),
        ("Kaito Leaderboard", "Leaderboard", "measures", "Rank", "Metric"),
        ("X", "SocialPlatform", "ranked_by", "Kaito Leaderboard", "Leaderboard"),
        ("Contribution", "Action", "affects", "Rank", "Metric"),
    ]
    
    for subj, subj_type, rel, obj, obj_type in points_data:
        handler.insert_triplet(
            subject=subj,
            subject_type=subj_type,
            relation=rel,
            obj=obj,
            obj_type=obj_type,
            source="manual_fix"
        )
    
    print("\n✓ Data added!")
    print("="*70 + "\n")
    
    handler.disconnect()