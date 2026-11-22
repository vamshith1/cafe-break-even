"""Café startup cost & break-even model.

A Python version of excel/Cafe_Break_Even_Model.xlsx. Every calculation follows
the same formulas as the workbook, so with the default inputs the results match
the Excel file to the rupee.

All amounts are in ₹ and exclude GST (cafés charge 5% GST without input tax
credit; that money goes to the government, not the café).
"""
from dataclasses import dataclass, replace

import pandas as pd

MONTHS = 36

# The three scenarios from the Scenarios sheet: footfall, bill, ingredient cost and rent.
PRESETS = {
    "Pessimistic": dict(customers_per_day=65, avg_bill=270, fb_cost=0.35, rent_per_sqft=140),
    "Base": dict(customers_per_day=90, avg_bill=300, fb_cost=0.32, rent_per_sqft=120),
    "Optimistic": dict(customers_per_day=120, avg_bill=330, fb_cost=0.30, rent_per_sqft=100),
}

# Reference data shown in the app (Assumptions sheet). Their totals are the defaults below.
STAFF = [
    # role, people, salary each (₹/month), source
    ("Café manager", 1, 35000, "Assumption"),
    ("Barista", 2, 22000, "Bengaluru job listings: ₹17,000–30,000 per month"),
    ("Cook", 1, 28000, "Indeed Bengaluru food-industry roles: ₹17,972–43,475 per month"),
    ("Kitchen helper", 1, 15000, "Indeed Bengaluru café roles: ₹12,000–25,000 per month"),
    ("Service staff", 2, 15000, "Indeed Bengaluru café roles: ₹12,000–25,000 per month"),
    ("Housekeeping", 1, 12000, "Assumption"),
]
OVERHEADS = [
    # item, ₹ per month
    ("Electricity", 30000),
    ("Water & cooking gas", 10000),
    ("Internet, POS & software", 4000),
    ("Marketing (social media, offers)", 25000),
    ("Repairs & maintenance", 8000),
    ("Accounting & compliance", 5000),
    ("Miscellaneous", 10000),
]


@dataclass(frozen=True)
class Inputs:
    # Scenario levers
    customers_per_day: float = 90        # at full capacity (month 6 onwards)
    avg_bill: float = 300                # ₹ per customer, excl. GST
    fb_cost: float = 0.32                # food & beverage ingredients, share of sales
    rent_per_sqft: float = 120           # ₹ per sq ft per month
    # Space & lease
    area_sqft: float = 800
    seats: int = 30
    deposit_months: float = 6
    fitout_rent_months: float = 2
    # Sales
    open_days: int = 30
    delivery_share: float = 0.15         # share of sales via Swiggy / Zomato
    delivery_commission: float = 0.25    # of delivery sales
    price_increase: float = 0.05         # menu prices, per year
    gst: float = 0.05                    # informational: sales exclude GST
    ramp: tuple = (0.40, 0.55, 0.70, 0.80, 0.90, 1.00)  # share of full capacity, months 1–6
    # Costs
    packaging: float = 0.02
    payment_fees: float = 0.005
    staff_salaries: float = sum(n * s for _, n, s, _ in STAFF)   # ₹164,000 per month
    benefits: float = 0.10               # of salaries
    overheads: float = sum(v for _, v in OVERHEADS)              # ₹92,000 per month
    cost_increase: float = 0.05          # rent and salaries, per year
    interiors_per_sqft: float = 1200
    contingency: float = 0.05            # of setup spend
    working_capital_months: float = 2


def with_preset(inputs: Inputs, name: str) -> Inputs:
    """Return a copy of inputs with one scenario's four levers applied."""
    return replace(inputs, **PRESETS[name])


# ---------------------------------------------------------------- building blocks

def monthly_rent(i: Inputs) -> float:
    return i.area_sqft * i.rent_per_sqft


def fixed_costs_year1(i: Inputs) -> float:
    """Rent + salaries + benefits + overheads (Break-Even!B18)."""
    return monthly_rent(i) + i.staff_salaries + i.staff_salaries * i.benefits + i.overheads


def variable_cost_share(i: Inputs) -> float:
    """Share of each bill spent on ingredients, packaging, payment fees and delivery commission."""
    return i.fb_cost + i.packaging + i.payment_fees + i.delivery_share * i.delivery_commission


def unit_economics(i: Inputs) -> pd.DataFrame:
    """What happens to one average bill."""
    b = i.avg_bill
    rows = [
        ("Average bill (excl. GST)", b),
        ("Food & beverage ingredients", -b * i.fb_cost),
        ("Packaging", -b * i.packaging),
        ("Payment fees", -b * i.payment_fees),
        ("Delivery commission (averaged over all orders)", -b * i.delivery_share * i.delivery_commission),
    ]
    rows.append(("Contribution per customer", b - sum(-v for _, v in rows[1:])))
    return pd.DataFrame(rows, columns=["Item", "Amount"])


def contribution_per_customer(i: Inputs) -> float:
    return i.avg_bill - i.avg_bill * variable_cost_share(i)


def startup_costs(i: Inputs) -> pd.DataFrame:
    """The 18 line items of the Startup Costs sheet (cost = quantity × rate)."""
    rent = monthly_rent(i)
    items = [
        ("Premises", "Security deposit (refundable)", i.deposit_months, rent, "Months of rent"),
        ("Premises", "Rent during fit-out", i.fitout_rent_months, rent, "Rent paid while interiors are done"),
        ("Interiors", "Interior fit-out (flooring, lighting, plumbing, painting)", i.area_sqft,
         i.interiors_per_sqft, "Area × rate per sq ft"),
        ("Interiors", "Signage & shopfront", 1, 75000, "Assumption"),
        ("Equipment", "Espresso machine (2-group, commercial)", 1, 250000,
         "Assumption; total café equipment is usually ₹2–8 lakh"),
        ("Equipment", "Coffee grinders", 2, 30000, "Assumption"),
        ("Equipment", "Refrigerator, freezer & display chiller", 1, 150000, "Assumption"),
        ("Equipment", "Kitchen equipment (oven, griddle, blenders, induction)", 1, 150000, "Assumption"),
        ("Equipment", "Water purifier & small tools", 1, 40000, "Assumption"),
        ("Furniture", "Tables & chairs (per seat)", i.seats, 6000, "Seats × ₹6,000"),
        ("Furniture", "Service counter & storage", 1, 100000, "Assumption"),
        ("Technology", "POS billing system & printers", 1, 45000, "Assumption"),
        ("Technology", "CCTV & music system", 1, 40000, "Assumption"),
        ("Licences", "Licences & registrations (FSSAI, trade licence, GST, fire NOC, shop & establishment)",
         1, 60000, "FSSAI from ₹100/yr; trade licence ₹2,000–5,000; rest assumption"),
        ("Launch", "Opening stock of ingredients & packaging", 1, 100000, "Assumption"),
        ("Launch", "Branding, menu design & launch marketing", 1, 120000, "Assumption"),
    ]
    df = pd.DataFrame(items, columns=["Category", "Item", "Quantity", "Rate", "Basis"])
    df["Cost"] = df["Quantity"] * df["Rate"]
    setup_spend = df.loc[2:, "Cost"].sum()          # interiors to launch (rows 6–19 in Excel)
    buffers = pd.DataFrame(
        [
            ("Buffers", "Contingency (overruns on setup spend)", i.contingency, setup_spend,
             "Share of setup spend"),
            ("Buffers", "Working capital reserve", i.working_capital_months, fixed_costs_year1(i),
             "Months of fixed costs, to survive the slow first months"),
        ],
        columns=["Category", "Item", "Quantity", "Rate", "Basis"],
    )
    buffers["Cost"] = buffers["Quantity"] * buffers["Rate"]
    return pd.concat([df, buffers], ignore_index=True)[["Category", "Item", "Quantity", "Rate", "Cost", "Basis"]]


def total_investment(i: Inputs) -> float:
    return float(startup_costs(i)["Cost"].sum())


def monthly_pnl(i: Inputs, months: int = MONTHS) -> pd.DataFrame:
    """Monthly profit & loss with ramp-up, yearly price/cost increases and cash position."""
    rows = []
    cash = -total_investment(i)
    rent0 = monthly_rent(i)
    for m in range(1, months + 1):
        year = (m - 1) // 12 + 1
        capacity = i.ramp[-1] if m >= len(i.ramp) else i.ramp[m - 1]
        customers_day = i.customers_per_day * capacity
        customers = customers_day * i.open_days
        bill = i.avg_bill * (1 + i.price_increase) ** (year - 1)
        sales = customers * bill
        delivery_sales = sales * i.delivery_share
        fb = sales * i.fb_cost
        packaging = sales * i.packaging
        fees = sales * i.payment_fees
        commission = delivery_sales * i.delivery_commission
        variable = fb + packaging + fees + commission
        gross = sales - variable
        rent = rent0 * (1 + i.cost_increase) ** (year - 1)
        salaries = i.staff_salaries * (1 + i.cost_increase) ** (year - 1)
        benefits = salaries * i.benefits
        fixed = rent + salaries + benefits + i.overheads
        profit = gross - fixed
        cash += profit
        rows.append({
            "Month": m, "Year": year, "Share of full capacity": capacity,
            "Customers per day": customers_day, "Customers in the month": customers,
            "Average bill": bill, "Sales": sales, "Delivery app sales": delivery_sales,
            "Food & beverage ingredients": fb, "Packaging": packaging, "Payment fees": fees,
            "Delivery app commission": commission, "Total variable costs": variable,
            "Gross profit": gross, "Rent": rent, "Staff salaries": salaries,
            "Staff benefits & meals": benefits, "Utilities, marketing & other overheads": i.overheads,
            "Total fixed costs": fixed, "Operating profit": profit,
            "Operating margin": profit / sales if sales else 0.0, "Cash position": cash,
        })
    return pd.DataFrame(rows).set_index("Month")


def payback_month(pnl: pd.DataFrame):
    """First month when the cash position reaches zero, or None within the horizon."""
    paid = pnl.index[pnl["Cash position"] >= 0]
    return int(paid[0]) if len(paid) else None


def yearly(pnl: pd.DataFrame) -> pd.DataFrame:
    y = pnl.groupby("Year")[["Sales", "Operating profit"]].sum()
    y["Operating margin"] = y["Operating profit"] / y["Sales"]
    return y


def summary(i: Inputs) -> dict:
    """The key results shown on the Summary sheet."""
    contribution = contribution_per_customer(i)
    fixed = fixed_costs_year1(i)
    if contribution > 0:
        be_month = fixed / contribution
        be_day = be_month / i.open_days
    else:                                   # every sale loses money: break-even is impossible
        be_month = be_day = float("inf")
    pnl = monthly_pnl(i)
    return {
        "investment": total_investment(i),
        "fixed_costs": fixed,
        "contribution": contribution,
        "contribution_margin": contribution / i.avg_bill if i.avg_bill else 0.0,
        "break_even_per_day": be_day,
        "break_even_per_month": be_month,
        "break_even_sales": be_month * i.avg_bill,
        "seat_turns": be_day / i.seats if i.seats else float("inf"),
        "expected_per_day": i.customers_per_day,
        "margin_of_safety": (i.customers_per_day - be_day) / i.customers_per_day if i.customers_per_day else 0.0,
        "profit_full_capacity": i.customers_per_day * i.open_days * contribution - fixed,
        "sales_full_capacity": i.customers_per_day * i.open_days * i.avg_bill,
        "payback_month": payback_month(pnl),
        "pnl": pnl,
        "yearly": yearly(pnl),
    }


def break_even_curve(i: Inputs, max_customers: int) -> pd.DataFrame:
    """Monthly sales and total costs at each footfall level (year-1 prices)."""
    fixed = fixed_costs_year1(i)
    rows = []
    for c in range(0, max_customers + 1):
        sales = c * i.avg_bill * i.open_days
        rows.append({"Customers per day": c, "Sales": sales,
                     "Total costs": fixed + sales * variable_cost_share(i)})
    return pd.DataFrame(rows)
