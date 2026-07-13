# PSE&G Historical Tariff Dataset Profile

## Overview
- **Years Covered**: 1999, 2003, 2010, 2018, 2024
- **Tariff Versions**: Tariff 13, Tariff 14, Tariff 15, Tariff 16, Tariff 17
- **Rate Schedules**: GLP, HTS, LPL, RHS, RLM, RS
- **Total Rows**: 282

## Missing Values
- `Tariff_Version`: 0
- `Year`: 0
- `Rate_Schedule`: 0
- `Component_Label`: 0
- `Base_Rate`: 0
- `With_SUT`: 59

## Duplicate Rows
- 31 exact duplicate rows (out of 282).
- There are also pseudo-duplicates where `Tariff_Version`, `Year`, `Rate_Schedule`, `Component_Label`, and `Base_Rate` are identical, but `With_SUT` differs (likely representing different taxation treatments for the same period).

## Component Labels
There are 51 distinct component labels. Many of them contain raw footnote text, boilerplate strings, or non-normalized descriptions. Examples include:
- `Annual Demand Charge: Bills are due on presentation subject to a late pay ment charge at the rate of % per monthly`
- `Annual Demand Charge: billing period in accordance with Section  of  the Standard Terms and Conditions Service to a`
- `Annual Demand Charge: for paperless billing, of the outstanding bill and subject to  a late payment charge at the rate of %`
- `Annual Demand Charge: per kilowatt of Annual Peak Demand`
- `Annual Demand Charge: per kilowatt of Duplicate Service Capacity`
- `Annual Demand Charge: per kilowatt of Monthly Peak Demand`
- `Annual Demand Charge: per kilowatt of highest Monthly Peak`
- `Annual Demand Charge: shall be in accordance with Section , Measurement of Electric Servic e, of the Standard Terms`
- `Service Charge: (c-) Addition of a Base Energy Charge of  cents ( cents including New`
- `Service Charge: (d-) A credit of  ( including SUT) per  kilowatt of Monthly Peak Demand shall apply`
- `Service Charge: (e-a) A monthly facilities charge as set forth in Section  of these Standard Terms`
- `Service Charge: Customer   in each mont h [ including New Jersey`
- `Service Charge: Customer   in each month [  including New Jersey Sales and`
- `Service Charge: Customer , in each month [,  including New Jersey Sales and`
- `Service Charge: Customer in each month [ including New Jersey Sales and Use`
- `Service Charge: Customer must commit to a one time expenditure of at least  times its electric bill for the  months`
- `Service Charge: Public Service, in accordance with Standard Te rms and Conditions, Section , Metering, for`
- `Service Charge: SBC by subtracting  cents ( cents with SUT), and`
- `Service Charge: as designated in Standard Terms and Conditions , Section , High Voltage Service, and`
- `Service Charge: be subject to a monthly Service Charge of  ( including SUT) in lieu of the`
- `Service Charge: customers Application/Agreement A credit of  ( including SUT) per kilowatt of`
- `Service Charge: designated in Standard Terms and Conditions, Section , High Voltage Service, and`
- `Service Charge: in each month [ including New Jersey Sales and Use Tax (SUT)]`
- `Service Charge: in each month for installations with a thr ee time period watthour meter, or  in each`
- `Service Charge: monthly Service Charg e of  ( including SUT) in lieu of the otherwise applicable Service`
- `Summer Demand Charge: **   **`
- `Summer Demand Charge: (d-) A credit of  ( including SUT) per  kilowatt of Monthly Peak Demand shall apply`
- `Summer Demand Charge: (h) Veterans Organization Service:   Pursuant to NJSA :-, when electric service is`
- `Summer Demand Charge: Act, NJS A :- et seq  Under NJSA : - , a qualified Veterans Organization shall be`
- `Summer Demand Charge: Bills are due on presentation subject to a late pay ment charge at the rate of % per monthly`
- `Summer Demand Charge: Distribution Charge Remainder`
- `Summer Demand Charge: Generation Capacity`
- `Summer Demand Charge: Including SUT`
- `Summer Demand Charge: Market Transition Charge`
- `Summer Demand Charge: Market Transition Charge ( )`
- `Summer Demand Charge: Off-Peak`
- `Summer Demand Charge: On-Peak`
- `Summer Demand Charge: Organization as defined by NJSA :-  as an organization dedicated to serving the needs of`
- `Summer Demand Charge: Total Kilowatt Charge`
- `Summer Demand Charge: Transmission Capacity`
- `Summer Demand Charge: accordance with Section , Measurement of Electric Service, of the Standard Terms and`
- `Summer Demand Charge: billing period in accordance with Section  of  the Standard Terms and Conditions Service to a`
- `Summer Demand Charge: for paperless billing, of the outstanding bill and subject to  a late payment charge at the rate of %`
- `Summer Demand Charge: monthly billing period in accordance with Section  of the Standard Terms and Conditions Service`
- `Summer Demand Charge: paperless billing, of the outstanding bill and subject to a late payment charge at the rate of % per`
- `Summer Demand Charge: per kilowatt of Monthly Peak Demand`
- `Summer Demand Charge: per kilowatt of On-Peak Monthly Peak Demand`
- `Summer Demand Charge: per monthly billing period in accordance with Section  of the Standard Terms and Conditions`
- `Summer Demand Charge: shall be in accordance with Section , Measurement of Electric Service, of the Standard Terms`
- `Volumetric Charge: The current adjustment factor for Subtransmission to High Voltage usage is %`
- `Volumetric Charge: adjustment factor for Subtransmission to High Voltage usage is %`
- `Volumetric Charge: and High Voltage Losses as detailed in the Standard Terms and Conditions, Section   The current`
- `Volumetric Charge: per kilowatt-hour`
- `Volumetric Charge: per kilowatthour`

## Normalization Strategy
The component labels contain extreme amounts of scraped PDF boilerplate. The normalization step will map items like `Service Charge: Customer in each month [ including New Jersey Sales and Use` simply to `customer_charge`.
Unrelated boilerplate like "Bills are due on presentation..." or "adjustment factor for Subtransmission" will be marked as `unrelated_boilerplate` or `notes` to exclude them from the actual numerical tariff sums.
