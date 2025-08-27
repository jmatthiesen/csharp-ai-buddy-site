"""
Streamlit UI for RSS Feed Monitor
Provides a simple web interface for managing RSS feed subscriptions and running feed checks.
"""

import streamlit as st
import json
from config import Config
from rss_feed_monitor import RSSFeedMonitor

# Load configuration and initialize monitor
config = Config.load()
monitor = RSSFeedMonitor(config)

st.title("RSS Feed Monitor UI")

menu = ["List Subscriptions", "Add Subscription", "Remove Subscription", "Check Feeds", "Cleanup Old Items"]
choice = st.sidebar.selectbox("Menu", menu)

if choice == "List Subscriptions":
    st.header("RSS Feed Subscriptions")
    subs = monitor.list_subscriptions()
    if not subs:
        st.info("No subscriptions found.")
    else:
        for sub in subs:
            st.write(f"**{sub.name}**: {sub.feed_url}")
            st.write(f"Enabled: {sub.enabled}")
            st.write(f"Tags: {', '.join(sub.tags or [])}")
            st.write("---")

elif choice == "Add Subscription":
    st.header("Add RSS Feed Subscription")
    feed_url = st.text_input("Feed URL")
    name = st.text_input("Feed Name")
    description = st.text_area("Description")
    tags = st.text_input("Tags (comma separated)")
    if st.button("Add Subscription"):
        tag_list = [t.strip() for t in tags.split(",") if t.strip()]
        success = monitor.add_subscription(feed_url, name, description, tag_list)
        if success:
            st.success("Subscription added successfully.")
        else:
            st.error("Failed to add subscription.")

elif choice == "Remove Subscription":
    st.header("Remove RSS Feed Subscription")
    subs = monitor.list_subscriptions()
    feed_urls = [sub.feed_url for sub in subs]
    feed_url = st.selectbox("Select Feed to Remove", feed_urls)
    if st.button("Remove Subscription"):
        success = monitor.remove_subscription(feed_url)
        if success:
            st.success("Subscription removed successfully.")
        else:
            st.error("Failed to remove subscription.")

elif choice == "Check Feeds":
    st.header("Check All Enabled RSS Feeds")
    if st.button("Run Daily Check"):
        stats = monitor.run_daily_check()
        st.json(stats)

elif choice == "Cleanup Old Items":
    st.header("Cleanup Old Processed Items")
    days = st.number_input("Days to Keep", min_value=1, value=30)
    if st.button("Cleanup"):
        deleted_count = monitor.cleanup_old_processed_items(days)
        st.success(f"Cleaned up {deleted_count} old processed item records.")
