"""
    This module contains the code for smart parking system
"""

import bisect
import datetime
import random
import time
import heapq

import streamlit as st

if "parking_slots" not in st.session_state:
    st.session_state["parking_slots"] = {
        f"{chr(65 + i)}{j+1}": "available" for i in range(10) for j in range(10)
    }
if "time_slots" not in st.session_state:
    st.session_state["time_slots"] = {
        f"{chr(65 + i)}{j+1}": [] for i in range(10) for j in range(10)
    }
if "vehicle_id" not in st.session_state:
    st.session_state["vehicle_id"] = set()
if "bookings" not in st.session_state:
    st.session_state["bookings"] = {}
if "slot_placeholders" not in st.session_state:
    st.session_state["slot_placeholders"] = {}
if "threshold" not in st.session_state:
    st.session_state["threshold"] = 1799


def is_overlapping(new_booking, bookings):
    """Function to check if the current time clashes with any booking"""
    new_start, new_end = new_booking
    sorted_bookings = sorted(bookings, key=lambda x: x[0])
    start_times = [slot[0] for slot in sorted_bookings]

    idx = bisect.bisect_left(start_times, new_start)

    overlap = False
    prev_gap, next_gap = None, None

    if idx > 0:
        _, _, prev_end = sorted_bookings[idx - 1]
        if new_start < prev_end:
            overlap = True
        else:
            prev_gap = new_start - prev_end

    if idx < len(sorted_bookings):
        next_start, _, _ = sorted_bookings[idx]
        if new_end > next_start:
            overlap = True
        else:
            next_gap = next_start - new_end

    return overlap, prev_gap, next_gap


def render_slot(slot_id):
    """Function to render a slot"""
    slot_status = st.session_state["parking_slots"][slot_id]
    color = "lightblue" if slot_status == "available" else "darkgrey"
    st.session_state["slot_placeholders"][slot_id].markdown(
        f"<div style='background-color:{color}; "
        f"padding:10px; text-align:center;'>{slot_id}</div>",
        unsafe_allow_html=True,
    )


def render_all_slots():
    """Function to render all slots"""
    cols = st.columns(10)
    # For each row (i) and column (j)
    for i in range(10):
        for j in range(10):
            slot_id = f"{chr(65 + i)}{j+1}"

            # Create a placeholder if not already present.
            if slot_id not in st.session_state["slot_placeholders"]:
                st.session_state["slot_placeholders"][slot_id] = cols[j].empty()

            render_slot(slot_id)


def allocate_slot(car_number, start, end, booking_type):
    """Function to allocate a slot"""
    available_slots = [
        slot for slot, status in st.session_state["parking_slots"].items()
        if status == "available"
    ]
    if available_slots:
        allocated_slot = random.choice(available_slots)
        st.session_state["parking_slots"][allocated_slot] = "booked"
        st.session_state["bookings"][car_number] = {
            "slot": allocated_slot,
            "start_time": start,
            "end_time": end,
            "Booking_type": booking_type,
        }
        # Insert the new booking into the min-heap for that slot.
        heapq.heappush(st.session_state["time_slots"][allocated_slot], (start, car_number, end))

        render_slot(allocated_slot)
        st.session_state["vehicle_id"].add(car_number)
        return allocated_slot
    return None


def hhmm_to_datetime(date_str, time_str):
    """Function that takes the hhmm input and returns the datetime object"""
    if len(time_str) != 4 or not time_str.isdigit():
        raise ValueError("Time string must be exactly 4 digits in HHMM format.")

    hour = int(time_str[:2])
    minute = int(time_str[2:])

    if not 0 <= hour <= 23:
        raise ValueError("Hour must be between 00 and 23.")
    if not 0 <= minute <= 59:
        raise ValueError("Minute must be between 00 and 59.")

    try:
        date_obj = datetime.datetime.strptime(date_str, "%d-%m-%y").date()
    except ValueError as e:
        raise ValueError("Date string must be in 'dd-mm-yy' format.") from e

    return datetime.datetime(
        year=date_obj.year,
        month=date_obj.month,
        day=date_obj.day,
        hour=hour,
        minute=minute,
    ).timestamp()


def smart_allocate_slot(car_number, start, end, booking_type):
    """Function to allocate a slot"""
    if car_number in st.session_state["vehicle_id"]:
        car_info = st.session_state["bookings"][car_number]
        if car_info["Booking_type"] == "booking":
            curr = time.time()
            if car_info["start_time"] <= curr < car_info["end_time"]:
                return -2, st.session_state["bookings"][car_number]["slot"]
        return -1, None

    ts = st.session_state["time_slots"]

    chosen_slot = None
    mini = float('inf')  # Initialize with infinity for finding the minimum gap.
    thresh = st.session_state["threshold"]
    for slot_id, bookings in ts.items():
        if not bookings:
            continue
        overlap, prev_gap, next_gap = is_overlapping((start, end), bookings)
        if not overlap:
            if prev_gap is None:
                curr_min = next_gap
            elif next_gap is None:
                curr_min = prev_gap
            else:
                curr_min = min(prev_gap, next_gap)
            # Choose the slot with the smallest sufficient gap.
            if curr_min is not None and curr_min < mini and curr_min >= thresh:
                mini = curr_min
                chosen_slot = slot_id

    if chosen_slot is None:
        # No slot with an appropriate gap was found, so allocate a fully available slot.
        return allocate_slot(car_number, start, end, booking_type), None

    st.session_state["bookings"][car_number] = {
        "slot": chosen_slot,
        "start_time": start,
        "end_time": end,
        "Booking_type": booking_type,
    }
    heapq.heappush(st.session_state["time_slots"][chosen_slot], (start, car_number, end))
    render_slot(chosen_slot)
    st.session_state["vehicle_id"].add(car_number)
    return chosen_slot, None


def deallocate_slot(car_number):
    """Function for deallocating a slot"""
    if car_number in st.session_state["bookings"]:
        allocated_slot = st.session_state["bookings"][car_number]["slot"]
        st.session_state["parking_slots"][allocated_slot] = "available"
        del st.session_state["bookings"][car_number]
        
        ts = st.session_state["time_slots"]
        # Remove the booking with the matching car_number.
        for slot_id, bookings in ts.items():
            for i, booking in enumerate(bookings):
                if booking[1] == car_number:
                    del st.session_state["time_slots"][slot_id][i]
                    heapq.heapify(st.session_state["time_slots"][slot_id])
                    break

        render_slot(allocated_slot)
        st.session_state["vehicle_id"].remove(car_number)
        return allocated_slot

    return None


def check_expired_bookings():
    """
    If a booking has exceeded its duration, deallocate that slot.
    """
    current_time = time.time()
    expired_cars = []
    for car_number, booking in list(st.session_state["bookings"].items()):
        if current_time >= booking["end_time"]:
            expired_cars.append(car_number)
    for car_number in expired_cars:
        deallocate_slot(car_number)

def main():
    """Main function for the Smart Parking System app."""
    st.title("Smart Parking System")

    with st.expander("Navigation", expanded=True):
        choice = st.radio(
            "Choose an action",
            ["Check In", "Pre Booking", "Check Out"],
            horizontal=True,
        )

    st.markdown(f"### Current Selection: {choice}")

    # Check for and clear out any expired bookings.
    check_expired_bookings()

    st.subheader("Parking Slots Layout")
    render_all_slots()

    if choice == "Check In":
        handle_check_in()
    elif choice == "Pre Booking":
        handle_pre_booking()
    elif choice == "Check Out":
        handle_check_out()


def handle_check_in():
    """Handle the 'Check In' action."""
    st.subheader("Check In")
    car_number = st.text_input("Vehicle Number")
    duration = st.number_input("Number of Hours", min_value=1, max_value=24, value=6)
    curr = time.time()
    if st.button("Check In"):
        if not car_number.strip():
            st.warning("Please enter a valid car number.")
            return

        allocated_slot, extra = smart_allocate_slot(
            car_number, curr, curr + duration * 3600, "checkin"
        )
        if allocated_slot == -2:
            st.success(f"Your slot is {extra}")
        elif allocated_slot == -1:
            st.error("Vehicle already allocated")
        elif allocated_slot:
            st.success(f"Slot {allocated_slot} allocated for {car_number}.")
        else:
            st.error("No available slots.")


def handle_pre_booking():
    """Handle the 'Pre Booking' action."""
    st.subheader("Pre Booking")
    car_number = st.text_input("Vehicle Number")
    in_date = st.date_input("Select In Date", datetime.date.today()).strftime("%d-%m-%y")
    in_time = st.text_input("In Time (HHMM)")

    out_date = st.date_input("Select Out Date", datetime.date.today()).strftime("%d-%m-%y")
    out_time = st.text_input("Out Time (HHMM)")

    if st.button("Pre Book"):
        if not car_number.strip():
            st.warning("Please enter a valid car number.")
            return

        start = hhmm_to_datetime(in_date, in_time)
        end = hhmm_to_datetime(out_date, out_time)

        if start < end:
            allocated_slot, extra = smart_allocate_slot(car_number, start, end, "booking")
            if allocated_slot == -1:
                st.error("Already allocated a slot for the vehicle")
            elif allocated_slot:
                st.success(
                    f"Slot {allocated_slot} pre-booked for {car_number} "
                    f"from {in_time} to {out_time}."
                )
            else:
                st.error("No available slots.")
        else:
            st.error("Out time must be greater than in time.")


def handle_check_out():
    """Handle the 'Check Out' action."""
    st.subheader("Check Out")
    car_number = st.text_input("Vehicle Number")

    if st.button("Check Out"):
        if not car_number.strip():
            st.warning("Please enter a valid car number.")
            return
        deallocated_slot = deallocate_slot(car_number)
        if deallocated_slot:
            st.success(f"Slot {deallocated_slot} deallocated for {car_number}.")
        else:
            st.error("Vehicle number not found in bookings.")


if __name__ == "__main__":
    main()
