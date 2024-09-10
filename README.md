# ![Logo](https://github.com/jampez77/Jet2/blob/main/logo.png "Jet2 Logo") 
Jet2 bookings for Home Assistant

This component provides details of a specified Jet2 booking and adds sensors to [Home Assistant](https://www.home-assistant.io/) which can be used in your own automations.

---

[![GitHub Release][releases-shield]][releases]
[![License][license-shield]](LICENSE.md)
[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg?style=for-the-badge)](https://github.com/custom-components/hacs)
![Project Maintenance][maintenance-shield]


Enjoying this? Help me out with a :beers: or :coffee:!

[![coffee](https://www.buymeacoffee.com/assets/img/custom_images/black_img.png)](https://www.buymeacoffee.com/whenitworks)


## Installation through [HACS](https://hacs.xyz/)

There is an active [PR](https://github.com/hacs/default/pull/2647) to get this into [HACS](https://hacs.xyz/), once that is merged then you can install the **Jet2** integration by searching for it there in HA instance.

Until then you will have to add this repository manually:

Go to HACS -> 3 dot menu -> Custom Repositories:- 

Paste `https://github.com/jampez77/Jet2` into Repository field and select `Integration`

Now you should be able to find it in HACS as normal.

You can install the **Jet2** integration by searching for it there in HA instance.

## Manual Installation
Use this route only if you do not want to use [HACS](https://hacs.xyz/) and love the pain of manually installing regular updates.
* Add the `jet2` folder in your `custom_components` folder

## Usage

Each entry requires a `booking reference`, `date of birth` and `surname`. These will be the same you use to view your booking on the Jet2 website.

## Contributing

Contirbutions are welcome from everyone! By contributing to this project, you help improve it and make it more useful for the community. Here's how you can get involved:

### How to Contribute

1. **Report Bugs**: If you encounter a bug, please open an issue with details about the problem and how to reproduce it.
2. **Suggest Features**: Have an idea for a new feature? I'd love to hear about it! Please open an issue to discuss it.
3. **Submit Pull Requests**: If you'd like to contribute code:
   - Fork the repository and create your branch from `main`.
   - Make your changes in the new branch.
   - Open a pull request with a clear description of what you’ve done.

---
## Data 
The integration will either create a new calendar or add events to an existing calendar for every instance that will have any flights and check-in open time, as well as payment due date and the booking expiration date. the booking expiration date is used as a marker for removing entities from HA. once the expiration date is within an hour of the current (HA's) time it will remove all entities for that booking. 
There is also a camera that will stream accommodation images when they are available. Additionally the following information is also made available to HA:

- departure
- region
- area
- resort
- make
- numberOfPassengers
	* numberOfAdults
	* numberOfChildren
	* numberOfInfants
- reservedSeats
- numberOfInclusiveBags
- numberOfAdditionalBags
- insurance
- bookedMeals
- bookingReference
- holidayType
- priceBreakdown
	* total
	* amountPaid
	* paymentDateDue
	* paidInFull
	* balance
	* travelEssentials
- hotel
	* name
	* rooms
		* description
		* quantity
	* board
		* description
- flightSummary
	* outbound / inbound
		* departureAirport
			* code
			* name
			* displayName
		* arrivalAirport
			* code
			* name
			* displayName
		* localDepartureDateTime
		* localArrivalDateTime
		* departureDateTimeUtc
		* arrivalDateTimeUtc
		* number
		* departureTerminal
			* name
		* arrivalTerminal
			* name
		* duration
			* hours
			* minutes
		* flightStatusId
		* passengers
			* id
			* passengerNameReference
			* seatNumber
			* sequenceNumber
			* checkedIn
- transferSummary
	* transferTypeId
	* transferTypeNameCode
	* isIncluded
- carHireSummaries
- numberOfFreeChildPlaces
- numberOfFreeInfantPlaces
- holidaySummaries
	* passenger
		* id
		* title
		* firstName
		* lastName
		* personType
		* personTypeCode
	* luggage
		* luggageType
		* luggageTypeCode
		* quantity
	* ancillaries
	* excursions
- holidayDuration
- checkInStatus
	* checkInDate
	* checkInAllowed
	* outboundFlight / inboundFlight
		* flightCheckInState
		* flightCheckInStateCode
		* checkedIn
		* checkedInCode
- scheduleChangeInfo
- accommodationExtrasSummaries
- expiryDate
- tradeAgentDetails
- hasResortFlightCheckIn
- isTradeBooking
- accommodationImages

---

[commits-shield]: https://img.shields.io/github/commit-activity/y/jampez77/Jet2.svg?style=for-the-badge
[commits]: https://github.com/jampez77/Jet2/commits/main
[license-shield]: https://img.shields.io/github/license/jampez77/Jet2.svg?style=for-the-badge
[maintenance-shield]: https://img.shields.io/badge/Maintainer-Jamie%20Nandhra--Pezone-blue
[releases-shield]: https://img.shields.io/github/v/release/jampez77/Jet2.svg?style=for-the-badge
[releases]: https://github.com/jampez77/Jet2/releases 
