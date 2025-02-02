import random
import time

import streamlit as st

if "parking_slots" not in st.session_state:
    # 10 x 10 grid of slots: A1 through J10
    st.session_state["parking_slots"] = {
        f"{chr(65 + i)}{j+1}": "available" for i in range(10) for j in range(10)
    }

    st.session_state["time_slots"] = {
        f"{chr(65 + i)}{j+1}": [] for i in range(10) for j in range(10)
    }

    st.session_state["vehicle_id"] = set()


if "bookings" not in st.session_state:
    st.session_state["bookings"] = {}

# This dictionary will store one placeholder per slot
if "slot_placeholders" not in st.session_state:
    st.session_state["slot_placeholders"] = {}


def is_overlapping(new_booking, bookings):
    new_start, new_end = new_booking
    start_times = [slot[0] for slot in bookings]
    
    idx = bisect.bisect_left(start_times, new_start)
    
    overlap = False
    prev_gap, next_gap = None, None
    
    if idx > 0:
        prev_start, prev_end = bookings[idx - 1]
        if new_start < prev_end:
            overlap = True
        else:
            prev_gap = (new_start - prev_end) / 3600
    
    if idx < len(bookings):
        next_start, next_end = bookings[idx]
        if new_end > next_start:
            overlap = True
        else:
            next_gap = (next_start - new_end) / 3600
    
    return overlap, prev_gap, next_gap


def render_slot(slot_id):
    slot_status = st.session_state["parking_slots"][slot_id]
    color = "lightblue" if slot_status == "available" else "darkgrey"
    st.session_state["slot_placeholders"][slot_id].markdown(
        f"<div style='background-color:{color}; "
        f"padding:10px; text-align:center;'>{slot_id}</div>",
        unsafe_allow_html=True,
    )


def render_all_slots():
    cols = st.columns(10)
    # For each row (i) and column (j)
    for i in range(10):
        for j in range(10):
            slot_id = f"{chr(65 + i)}{j+1}"

            # If this placeholder does not exist yet, create it
            if slot_id not in st.session_state["slot_placeholders"]:
                st.session_state["slot_placeholders"][slot_id] = cols[j].empty()

            # Render the slot status into the placeholder
            render_slot(slot_id)


def allocate_slot(car_number, car_type, duration):
    if car_number in st.session_state["vehicle_id"]:
        return -1
    available_slots = [
        slot
        for slot, status in st.session_state["parking_slots"].items()
        if status == "available"
    ]
    if available_slots:
        allocated_slot = random.choice(available_slots)
        st.session_state["parking_slots"][allocated_slot] = "booked"
        start = time.time()
        end = time.time() + int(duration) * 3600
        st.session_state["bookings"][car_number] = {
            "slot": allocated_slot,
            "Vehicle_type": car_type,
            "start_time": start,
            "end_time": end,
        }
        st.session_state["time_slots"][allocated_slot].append([car_number, start, end])
        render_slot(allocated_slot)
        st.session_state["vehicle_id"].add(car_number)
        return allocated_slot
    return None


def deallocate_slot(car_number):
    if car_number in st.session_state["bookings"]:
        allocated_slot = st.session_state["bookings"][car_number]["slot"]
        st.session_state["parking_slots"][allocated_slot] = "available"
        del st.session_state["bookings"][car_number]
        # Re-render just this slot
        render_slot(allocated_slot)
        return allocated_slot

    return None


def check_expired_bookings():
    """
    If a booking has exceeded its duration, deallocate that slot.
    """

    current_time = time.time()
    expired_cars = []
    for car_number, booking in st.session_state["bookings"].items():
        # Convert duration (hours) to seconds for comparison
        if current_time - booking["start_time"] >= booking["duration"] * 3600:
            expired_cars.append(car_number)
    for car_number in expired_cars:
        deallocate_slot(car_number)


def main():
    st.title("Smart Parking System")

    # Navigation
    with st.expander("Navigation", expanded=True):
        choice = st.radio(
            "Choose an action",
            ["Check In", "Pre Booking", "Check Out"],
            horizontal=True,
        )

    st.markdown(f"### Current Selection: {choice}")

    # Check for expired bookings before rendering slots
    check_expired_bookings()

    # Render the 10x10 grid of slots
    st.subheader("Parking Slots Layout")
    render_all_slots()

    # Actions depending on user choice
    if choice == "Check In":
        st.subheader("Check In")
        car_number = st.text_input("Vehicle Number")
        car_type = st.selectbox(
            "Vehicle Type", ["2 wheeler", "4 wheeler", "EV-4 wheeler"]
        )
        duration = st.number_input(
            "Number of Hours", min_value=1, max_value=24, value=6
        )
        if st.button("Check In"):
            if not car_number.strip():
                st.warning("Please enter a valid car number.")
            else:
                allocated_slot = allocate_slot(car_number, car_type, duration)
                if allocated_slot == -1:
                    st.error("Vehicle already allocated")
                elif allocated_slot:
                    st.success(f"Slot {allocated_slot} allocated for {car_number}.")
                else:
                    st.error("No available slots.")

    elif choice == "Pre Booking":
        st.subheader("Pre Booking")
        car_number = st.text_input("Vehicle Number")
        car_type = st.selectbox(
            "Vehicle Type", ["2 wheeler", "4 wheeler", "EV-4 wheeler"]
        )
        in_time = st.number_input("In Time (HH)", min_value=0, max_value=23, value=10)
        out_time = st.number_input("Out Time (HH)", min_value=0, max_value=23, value=16)
        if st.button("Pre Book"):
            if not car_number.strip():
                st.warning("Please enter a valid car number.")
            else:
                duration = out_time - in_time
                if duration > 0:
                    allocated_slot = allocate_slot(car_number, car_type, duration)
                    if allocated_slot:
                        st.success(
                            f"Slot {allocated_slot} pre-booked for {car_number} "
                            f"from {in_time}:00 to {out_time}:00."
                        )
                    else:
                        st.error("No available slots.")
                else:
                    st.error("Out time must be greater than in time.")

    elif choice == "Check Out":
        st.subheader("Check Out")
        car_number = st.text_input("Vehicle Number")
        if st.button("Check Out"):
            if not car_number.strip():
                st.warning("Please enter a valid car number.")
            else:
                deallocated_slot = deallocate_slot(car_number)
                if deallocated_slot:
                    st.success(f"Slot {deallocated_slot} deallocated for {car_number}.")
                else:
                    st.error("Vehicle number not found in bookings.")


if __name__ == "__main__":
    main()
