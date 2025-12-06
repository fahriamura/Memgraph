import schedule
import time
from datetime import datetime
from main import KnowledgeGraphUpdater
from config import SCRAPE_INTERVAL_HOURS

def scheduled_update():

    print(f"\n{'='*70}")
    print(f"SCHEDULED UPDATE STARTED: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print('='*70)
    
    updater = KnowledgeGraphUpdater()
    success = updater.run_full_update()
    
    if success:
        print(f"\nScheduled update completed successfully")
    else:
        print(f"\nScheduled update failed")
    
    print(f"Next update in {SCRAPE_INTERVAL_HOURS} hours")

def start_scheduler():

    print("\n" + "="*70)
    print("IRYS KNOWLEDGE GRAPH AUTO-UPDATER")
    print("="*70)
    print(f"Update interval: Every {SCRAPE_INTERVAL_HOURS} hours")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\nPress Ctrl+C to stop\n")

    schedule.every(SCRAPE_INTERVAL_HOURS).hours.do(scheduled_update)
    
   
    print("Running initial update...")
    scheduled_update()

    try:
        while True:
            schedule.run_pending()
            time.sleep(60) 
    except KeyboardInterrupt:
        print("\n\n✓ Scheduler stopped")

if __name__ == "__main__":
    start_scheduler()