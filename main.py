"""
Main script to run daily MLB hit predictions and send via SMS
"""

from mlb_hit_predictor import MLBHitPredictor
from sms_sender import send_daily_picks


def main():
    """
    Main function:
    1. Get today's top 5 hit predictions
    2. Format message
    3. Send via SMS (only if picks are available)
    """
    print("Starting MLB Hit Predictor...")
    
    # Create predictor
    predictor = MLBHitPredictor()
    
    # Get top 5 picks
    print("Analyzing today's games...")
    picks = predictor.get_top_picks(limit=5)
    
    # Format message
    message = predictor.format_picks_message(picks)
    
    # Only send if we have a valid message
    if message is None or not message:
        print("No lineups available yet - skipping SMS")
        print("This is normal - lineups are usually posted 1-2 hours before first pitch")
        return 0
    
    print(f"\n{message}\n")
    
    # Send SMS
    print("Sending SMS...")
    success = send_daily_picks(message)
    
    if success:
        print("✓ Daily picks sent successfully!")
        return 0
    else:
        print("✗ Failed to send picks")
        return 1


if __name__ == "__main__":
    exit(main())
