"""
    This module contains the code for smart parking system
"""

import bisect
import datetime
import random
import time

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


def is_overlapping(new_booking, bookings):
    """Function to check if the current time clashes with any booking"""
    new_start, new_end = new_booking
    start_times = [slot[1] for slot in bookings]

    idx = bisect.bisect_left(start_times, new_start)

    overlap = False
    prev_gap, next_gap = None, None

    if idx > 0:
        _, _, prev_end = bookings[idx - 1]
        if new_start < prev_end:
            overlap = True
        else:
            prev_gap = new_start - prev_end

    if idx < len(bookings):
        _, next_start, _ = bookings[idx]
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

            # If this placeholder does not exist yet, create it
            if slot_id not in st.session_state["slot_placeholders"]:
                st.session_state["slot_placeholders"][slot_id] = cols[j].empty()

            # Render the slot status into the placeholder
            render_slot(slot_id)


def allocate_slot(car_number, start, end, booking_type):
    """Function to allocate a slot"""
    available_slots = [
        slot
        for slot, status in st.session_state["parking_slots"].items()
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
        st.session_state["time_slots"][allocated_slot].append([car_number, start, end])
        st.session_state["time_slots"][allocated_slot].sort(key=lambda slot: slot[1])

        render_slot(allocated_slot)
        st.session_state["vehicle_id"].add(car_number)
        st.success(f"Slot {str(allocated_slot)} pre-booked for {car_number}")
        return
    st.error("No slots available")


def smart_allocate_slot(car_number, start, end, booking_type):
    """Function to allocate a slot"""

    if car_number in st.session_state["vehicle_id"]:
        car_info = st.session_state["bookings"][car_number]
        if booking_type == "checkin":
            curr = time.time()
            if car_info["start_time"] <= curr < car_info["end_time"]:
                st.success(
                    f'Your slot is {st.session_state["bookings"][car_number]["slot"]}'
                )
                return
            st.error("Time se aa bsdk")
            return
        if booking_type == "booking":
            st.error("Already allocated a slot for the vehicle")
            return
        st.error("Invalid booking type")
        return

    ts = st.session_state["time_slots"]

    ind = -1
    mini = time.time()
    thresh = st.session_state["threshold"]
    for i in st.session_state["time_slots"].keys():
        if len(ts[i]) == 0:
            continue
        overlap, prev_gap, next_gap = is_overlapping(
            (start, end), st.session_state["time_slots"][i]
        )
        if not overlap:
            if prev_gap is None:
                curr_min = next_gap
            elif next_gap is None:
                curr_min = prev_gap
            else:
                curr_min = min(prev_gap, next_gap)

            if curr_min < mini:
                if curr_min >= thresh:
                    ind = i
    if ind == -1:
        allocate_slot(car_number, start, end, booking_type)
        return

    st.session_state["bookings"][car_number] = {
        "slot": ind,
        "start_time": start,
        "end_time": end,
        "Booking_type": booking_type,
    }
    st.session_state["time_slots"][ind].append([car_number, start, end])
    st.session_state["time_slots"][ind].sort(key=lambda slot: slot[1])
    render_slot(ind)
    st.session_state["vehicle_id"].add(car_number)
    st.session_state["parking_slots"][ind] = "booked"
    st.success(f"Slot {ind} pre-booked for {car_number}")


def deallocate_slot(car_number):
    """Function for deallocating a slot"""
    if car_number in st.session_state["bookings"]:
        allocated_slot = st.session_state["bookings"][car_number]["slot"]
        st.session_state["parking_slots"][allocated_slot] = "available"
        del st.session_state["bookings"][car_number]
        # Re-render just this slot
        ts = st.session_state["time_slots"]

        for key in st.session_state["time_slots"].keys():
            for i, slot in enumerate(ts[key]):
                if slot[0] == car_number:
                    del st.session_state["time_slots"][key][i]
                    break

        # for i, slot in enumerate(st.session_state["time_slots"]):
        #     if slot[0]==car_number:
        #         del st.session_state["time_slots"][i]
        render_slot(allocated_slot)
        st.session_state["vehicle_id"].remove(car_number)
        return allocated_slot

    return None


# def check_expired_bookings():
#     """
#     If a booking has exceeded its duration, deallocate that slot.
#     """
#     current_time = time.time()
#     expired_cars = []
#     for car_number, booking in st.session_state["bookings"].items():
#         if current_time >= booking["end_time"]:
#             expired_cars.append(car_number)
#     for car_number in expired_cars:
#         deallocate_slot(car_number)


def main():
    """Main function for the Smart Parking System app."""
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
    # check_expired_bookings()

    # Render the 10x10 grid of slots
    st.subheader("Parking Slots Layout")
    render_all_slots()

    # Display the appropriate section based on the user’s selection
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

        smart_allocate_slot(car_number, curr, curr + duration * 3600, "checkin")


def handle_pre_booking():
    """Handle the 'Pre Booking' action."""
    st.subheader("Pre Booking")
    car_number = st.text_input("Vehicle Number")
    in_date = st.date_input("Select In Date", datetime.date.today()).strftime(
        "%d-%m-%y"
    )
    in_time = st.text_input("In Time (HHMM)")

    out_date = st.date_input("Select Out Date", datetime.date.today()).strftime(
        "%d-%m-%y"
    )
    out_time = st.text_input("Out Time (HHMM)")

    if st.button("Pre Book"):
        if not car_number.strip():
            st.warning("Please enter a valid car number.")
            return

        start = hhmm_to_datetime(in_date, in_time)
        end = hhmm_to_datetime(out_date, out_time)

        if start < end:
            smart_allocate_slot(car_number, start, end, "booking")
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
