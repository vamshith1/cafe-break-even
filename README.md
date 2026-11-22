# Café Break-Even Calculator — Kaapi Corner, Bengaluru

An interactive startup cost and break-even model for opening an 800 sq ft, 30-seat café in HSR Layout, Bengaluru. Move the sliders (customers per day, average bill, ingredient cost, rent and more) and every result updates instantly.

**Live app:** https://vn-cafe-break-even.streamlit.app

It answers three questions:

1. **How much money is needed to open?** → ₹39.5 lakh
2. **How many customers a day does it need to stop losing money?** → 66 customers per day
3. **When does the café earn back its investment?** → Month 34 (base case)

The app is the web version of an Excel model ([`excel/Cafe_Break_Even_Model.xlsx`](excel/Cafe_Break_Even_Model.xlsx)) with the same formulas. Checked against the workbook, it matches on **1,416 values** across all three scenarios: startup costs, break-even and all 36 months of profit and cash.

## Key results (base case)

| Result | Value |
|---|---|
| Total investment needed | ₹39.51 lakh |
| Monthly fixed costs (year 1) | ₹3,68,400 |
| Average bill (excl. GST) | ₹300 |
| Contribution per customer | ₹185.25 (61.75% of the bill) |
| **Break-even** | **66.3 customers per day** (₹5.97 lakh sales per month) |
| Expected customers per day | 90 (reached in month 6) |
| Margin of safety | 26.3% |
| Monthly operating profit at full capacity | ₹1,31,775 (16.3% of ₹8.1 lakh sales) |
| **Payback** | **Month 34** |

| Scenario | Customers/day | Bill | Ingredients | Rent/sq ft | Break-even/day | Monthly profit | Payback |
|---|---|---|---|---|---|---|---|
| Pessimistic | 65 | ₹270 | 35% | ₹140 | 80.8 | −₹75,081 | Not within 3 years |
| **Base** | 90 | ₹300 | 32% | ₹120 | 66.3 | ₹1,31,775 | Month 34 |
| Optimistic | 120 | ₹330 | 30% | ₹100 | 55.8 | ₹4,04,950 | Month 13 |

**Main insight:** footfall decides everything. In the pessimistic case the café expects 65 customers a day but needs 81, so it loses money every month. That's the number to test before signing a lease.

## What's in the app

| Tab | Shows |
|---|---|
| **Verdict + KPIs** | Viable / loss-making at a glance; investment, break-even, margin of safety, monthly profit, payback, with changes vs the base case |
| **Break-even** | Sales vs total costs chart, what happens to one ₹300 bill, fixed costs, and how break-even moves with the bill and the rent |
| **Cash & payback** | Monthly operating profit (ramp-up losses, then profit) and the cash position climbing back to zero |
| **Startup costs** | All 18 items (quantity × rate) and totals by category |
| **Monthly P&L** | 36-month profit & loss, downloadable as CSV |
| **Scenarios** | Pessimistic vs base vs optimistic side by side |
| **About & sources** | Method, staff and overhead assumptions, limits and links to every source |

The sidebar also has a **Download the Excel model** button.

## How it works

1. **Startup costs:** 18 items, each quantity × rate (deposit = 6 months' rent, interiors = area × ₹1,200/sq ft, tables & chairs = seats × ₹6,000…), plus a 5% contingency and a 2-month working capital reserve.
2. **Contribution per customer:** the ₹300 bill minus ingredients (32%), packaging (2%), payment fees (0.5%) and delivery commission (15% of orders × 25%) = ₹185.25.
3. **Break-even:** monthly fixed costs ÷ contribution per customer ÷ 30 days = 66.3 customers a day.
4. **Monthly P&L:** customers ramp up from 40% of capacity in month 1 to 100% by month 6; menu prices, rent and salaries rise 5% a year.
5. **Payback:** the cash position starts at −₹39.5 lakh and adds each month's operating profit. Payback is the month it reaches zero.

All amounts exclude GST: cafés charge 5% GST without input tax credit, and that money goes to the government. Operating profit is before depreciation, loan interest and income tax.

## Project structure

```
├── app.py                          # Streamlit web app
├── model.py                        # the model's formulas in Python (same as the Excel)
├── excel/Cafe_Break_Even_Model.xlsx  # the original Excel model (7 sheets, live formulas)
├── requirements.txt
└── .streamlit/config.toml          # theme
```

## Run it locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Data sources

Rent: [Address Advisors](https://addressadvisors.com/forum/commercial-rent-per-square-foot-in-bangalore) (HSR Layout ₹60–140/sq ft) · Salaries: [Apna](https://apna.co/job/bengaluru-bangalore/barista-440942640), [Indeed](https://in.indeed.com/Cafe-jobs-in-Bengaluru,-Karnataka) · Ingredient cost: [Kaapi Machines](https://kaapimachines.com/cafe-business-management-growth/), [Restaurant India](https://www.restaurantindia.in/article/cafe-profit-margin-in-india-what-to-realistically-expect.16906) · Average bill: [Rajiv Talreja](https://rajivtalreja.com/blog/cafe-vs-restaurant-business/) · Startup & licence costs: [Petpooja](https://blog.petpooja.com/free-tools/cafe-startup-cost-calculator-free/), [Restroworks](https://www.restroworks.com/blog/?p=15772) · GST: [Razorpay](https://razorpay.com/learn/gst-on-food-and-restaurants/). Researched November 2026. Figures without a source are assumptions, marked as such in the Excel model.

## Limits

- Public benchmarks, not broker or supplier quotes; rent varies street by street.
- No seasonality, loan interest, depreciation or income tax.

## Resume lines

> **Café Startup Cost & Break-Even Model** (Excel, Python, Streamlit) · [Live app](https://vn-cafe-break-even.streamlit.app)
> - Built a 36-month financial model for a 30-seat café in Bengaluru covering ₹39.5 lakh startup costs, unit economics and monthly P&L, using benchmarks from 11 industry and job-market sources.
> - Calculated break-even at 66 customers/day and payback in 34 months; built pessimistic, base and optimistic scenarios, showing the café is loss-making below 81 customers/day in the pessimistic case.
> - Turned the Excel model into an interactive web app with live sliders and charts, verified against the workbook on 1,416 values.
