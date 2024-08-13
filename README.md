# ![Logo](https://github.com/jampez77/Jet2/blob/main/logo.png "Jet2 Logo") Jet2 bookings for Home Assistant

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

---
## Data 
The following attributes can be expose as attributes in HA. It's also worth mentioning that some data won't be returned if it doesn't apply to the specific vehicle.

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

---

[commits-shield]: https://img.shields.io/github/commit-activity/y/jampez77/Jet2.svg?style=for-the-badge
[commits]: https://github.com/jampez77/Jet2/commits/main
[license-shield]: https://img.shields.io/github/license/jampez77/Jet2.svg?style=for-the-badge
[maintenance-shield]: https://img.shields.io/badge/Maintainer-Jamie%20Nandhra--Pezone-blue
[releases-shield]: https://img.shields.io/github/v/release/jampez77/Jet2.svg?style=for-the-badge
[releases]: https://github.com/jampez77/Jet2/releases 
