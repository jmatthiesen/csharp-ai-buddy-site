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

menu = ["List Subscriptions", "Add Subscription", "Remove Subscription", "Check Feeds", 
        "Pending Items", "Cleanup Old Items"]
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
        tag_list = [t.strip() for t in (tags or '').split(",") if t.strip()]
        success = monitor.add_subscription(feed_url, name, description, tag_list)
        if success:
            st.success("Subscription added successfully.")
        else:
            st.error("Failed to add subscription.")

elif choice == "Remove Subscription":
    st.header("Remove RSS Feed Subscription")
    subs = monitor.list_subscriptions()
    feed_urls = [sub.feed_url for sub in subs]
    if feed_urls:
        feed_url = st.selectbox("Select Feed to Remove", feed_urls)
        if st.button("Remove Subscription"):
            success = monitor.remove_subscription(feed_url)
            if success:
                st.success("Subscription removed successfully.")
            else:
                st.error("Failed to remove subscription.")
    else:
        st.info("No subscriptions found.")

elif choice == "Check Feeds":
    st.header("Check All Enabled RSS Feeds")
    auto_ingest = st.checkbox("Auto-ingest new items (skip approval)", value=False)
    if st.button("Run Daily Check"):
        with st.spinner("Checking feeds..."):
            stats = monitor.run_daily_check(auto_ingest=auto_ingest)
        st.json(stats)
        if not auto_ingest and stats.get("total_items_queued", 0) > 0:
            st.info(f"✓ {stats['total_items_queued']} new items queued for approval. Go to 'Pending Items' to review.")

elif choice == "Pending Items":
    st.header("Pending Items for Approval")
    
    # Get pending items
    pending_items = monitor.get_pending_items()
    
    if not pending_items:
        st.info("No pending items found.")
    else:
        st.write(f"**{len(pending_items)} items pending approval**")
        
        # Create checkboxes for each item
        st.write("---")
        
        # Store selections in session state
        if 'selected_items' not in st.session_state:
            st.session_state.selected_items = set()
        
        # Add select/deselect all buttons
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Select All"):
                st.session_state.selected_items = {item['item_id'] for item in pending_items}
                st.rerun()
        with col2:
            if st.button("Deselect All"):
                st.session_state.selected_items = set()
                st.rerun()
        
        st.write("---")
        
        # Display items with checkboxes
        for item in pending_items:
            item_id = item['item_id']
            is_selected = item_id in st.session_state.selected_items
            
            # Create a container for each item
            with st.container():
                col1, col2 = st.columns([1, 20])
                
                with col1:
                    # Checkbox for selection
                    if st.checkbox("", value=is_selected, key=f"cb_{item_id}"):
                        st.session_state.selected_items.add(item_id)
                    else:
                        st.session_state.selected_items.discard(item_id)
                
                with col2:
                    # Item details
                    st.write(f"**{item['title']}**")
                    st.write(f"Feed: {item['feed_name']}")
                    st.write(f"Link: [{item['link']}]({item['link']})")
                    st.write(f"Published: {item.get('published_date', 'Unknown')}")
                    
                    # Show description in an expander
                    with st.expander("Show description"):
                        st.write(item.get('description', 'No description available'))
                
                st.write("---")
        
        # Action buttons
        st.write("### Actions")
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("✓ Approve Selected", type="primary"):
                selected_ids = list(st.session_state.selected_items)
                if selected_ids:
                    with st.spinner(f"Approving and ingesting {len(selected_ids)} items..."):
                        result = monitor.approve_items(selected_ids)
                    st.success(f"Approved {result['approved_count']} items")
                    if result['failed_count'] > 0:
                        st.error(f"Failed to approve {result['failed_count']} items")
                        for error in result['errors']:
                            st.error(error)
                    # Clear selections
                    st.session_state.selected_items = set()
                    st.rerun()
                else:
                    st.warning("No items selected")
        
        with col2:
            if st.button("✗ Reject Selected"):
                selected_ids = list(st.session_state.selected_items)
                if selected_ids:
                    with st.spinner(f"Rejecting {len(selected_ids)} items..."):
                        result = monitor.reject_items(selected_ids)
                    st.success(f"Rejected {result['rejected_count']} items")
                    if result['failed_count'] > 0:
                        st.error(f"Failed to reject {result['failed_count']} items")
                    # Clear selections
                    st.session_state.selected_items = set()
                    st.rerun()
                else:
                    st.warning("No items selected")

elif choice == "Cleanup Old Items":
    st.header("Cleanup Old Processed Items")
    days = st.number_input("Days to Keep", min_value=1, value=30)
    if st.button("Cleanup"):
        deleted_count = monitor.cleanup_old_processed_items(days)
        st.success(f"Cleaned up {deleted_count} old processed item records.")
