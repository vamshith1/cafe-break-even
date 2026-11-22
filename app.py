"""Café Break-Even Calculator — Streamlit app.

Run locally:  streamlit run app.py
"""
import importlib
from dataclasses import replace
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

import model as model_module

# Streamlit re-runs app.py after a code update but keeps imported modules in memory;
# reload the model so changes to model.py take effect without a reboot.
importlib.reload(model_module)
from model import (  # noqa: E402
    MONTHS, OVERHEADS, PRESETS, STAFF, Inputs, break_even_curve, contribution_per_customer,
    fixed_costs_year1, startup_costs, summary, unit_economics, with_preset,
)

ROOT = Path(__file__).parent
EXCEL = ROOT / "excel" / "Cafe_Break_Even_Model.xlsx"
REPO = "https://github.com/vamshith1/cafe-break-even"

# Chart colours (readable on light and dark backgrounds)
SALES, COSTS, LOSS, GAIN, EXPECTED = "#C8743A", "#7C8798", "#D9534F", "#3C9A5F", "#3C9A5F"

st.set_page_config(page_title="Café Break-Even Calculator", page_icon="☕", layout="wide")
# Five KPI cards share one row: use a slightly smaller value font, and let a value wrap onto a
# second line on medium-width screens instead of being cut off with "…".
st.markdown(
    "<style>[data-testid='stMetricValue']{font-size:1.75rem}"
    "[data-testid='stMetricValue'] *{white-space:normal!important;overflow:visible!important;"
    "text-overflow:clip!important}</style>",
    unsafe_allow_html=True,
)


# ------------------------------------------------------------------ formatting
def inr(x: float, decimals: int = 0) -> str:
    """₹ with Indian digit grouping: 3951300 -> ₹39,51,300."""
    if x != x or x in (float("inf"), float("-inf")):
        return "—"
    sign = "−" if x < 0 else ""
    whole, _, frac = f"{abs(x):.{decimals}f}".partition(".")
    if len(whole) > 3:
        head, tail, parts = whole[:-3], whole[-3:], []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        whole = ",".join(parts + [tail])
    return f"{sign}₹{whole}" + (f".{frac}" if frac else "")


def lakh(x: float, decimals: int = 2) -> str:
    return f"{'−' if x < 0 else ''}₹{abs(x) / 1e5:,.{decimals}f} lakh"


def pct(x: float) -> str:
    if x != x or abs(x) == float("inf"):
        return "—"
    return f"{'−' if x < 0 else ''}{abs(x) * 100:.1f}%"


def per_day(x: float) -> str:
    return "Never" if x == float("inf") else f"{x:,.1f}"


def payback_text(m) -> str:
    return f"Month {m}" if m else "Not within 3 years"


def delta(cur: float, base: float, fmt) -> str | None:
    """Signed change vs the base case, or None when nothing changed."""
    if cur in (float("inf"), float("-inf")) or base in (float("inf"), float("-inf")):
        return None
    d = cur - base
    if abs(d) < 1e-9:
        return None
    return f"{'-' if d < 0 else '+'}{fmt(abs(d))} vs base"


# ------------------------------------------------------------------ inputs
DEFAULTS = dict(
    scenario="Base", customers=90, bill=300, fb=32, rent=120,
    area=800, seats=30, deposit=6, fitout=2, interiors=1200,
    delivery_share=15, commission=25, price_inc=5, cost_inc=5,
    salaries=int(Inputs().staff_salaries), overheads=int(Inputs().overheads), wc_months=2,
)
LEVERS = ("customers", "bill", "fb", "rent")


def preset_values(name: str) -> dict:
    p = PRESETS[name]
    return dict(customers=p["customers_per_day"], bill=p["avg_bill"],
                fb=round(p["fb_cost"] * 100), rent=p["rent_per_sqft"])


def apply_scenario():
    st.session_state.update(preset_values(st.session_state.scenario))


def reset_all():
    st.session_state.update(DEFAULTS)


for k, v in DEFAULTS.items():
    st.session_state.setdefault(k, v)
s = st.session_state

with st.sidebar:
    st.header("Your café")
    st.radio("Scenario", list(PRESETS), key="scenario", on_change=apply_scenario, horizontal=True,
             help="Loads footfall, bill, ingredient cost and rent for that scenario. Fine-tune them below.")
    st.slider("Customers per day (from month 6)", 20, 250, step=5, key="customers",
              help="Full-capacity footfall. A new café ramps up: 40% in month 1, 100% by month 6.")
    st.slider("Average bill per customer (₹, excl. GST)", 100, 800, step=10, key="bill")
    st.slider("Ingredient cost (% of sales)", 20, 45, step=1, key="fb", format="%d%%",
              help="Food and beverage ingredients. Cafés usually run 28–35%.")
    st.slider("Rent (₹ per sq ft per month)", 40, 300, step=5, key="rent",
              help="HSR Layout ₹60–140, Koramangala ₹70–150, prime high streets more.")
    with st.expander("Space & lease"):
        st.slider("Café area (sq ft)", 300, 2000, step=50, key="area")
        st.slider("Seats", 10, 100, step=2, key="seats")
        st.slider("Security deposit (months of rent)", 0, 12, key="deposit")
        st.slider("Rent paid during fit-out (months)", 0, 6, key="fitout")
        st.number_input("Interior fit-out (₹ per sq ft)", min_value=300, max_value=5000, step=100, key="interiors")
    with st.expander("Sales mix & growth"):
        st.slider("Sales via Swiggy / Zomato", 0, 60, key="delivery_share", format="%d%%")
        st.slider("Delivery app commission", 0, 35, key="commission", format="%d%%")
        st.slider("Menu price increase per year", 0, 15, key="price_inc", format="%d%%")
        st.slider("Rent & salary increase per year", 0, 15, key="cost_inc", format="%d%%")
    with st.expander("Monthly costs"):
        st.number_input("Staff salaries (₹ per month)", min_value=0, max_value=2_000_000, step=5000, key="salaries",
                        help="Base case: 9 people — manager, 2 baristas, cook, kitchen helper, 2 service staff, housekeeping.")
        st.number_input("Utilities, marketing & other overheads (₹ per month)", min_value=0, max_value=2_000_000,
                        step=5000, key="overheads",
                        help="Electricity, water & gas, internet & POS, marketing, repairs, accounting, miscellaneous.")
        st.slider("Working capital reserve (months of fixed costs)", 0, 6, key="wc_months")
    st.button("Reset to base case", on_click=reset_all)
    st.divider()
    if EXCEL.exists():
        st.download_button("Download the Excel model", EXCEL.read_bytes(), file_name="Cafe_Break_Even_Model.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                           help="The full workbook with live formulas (base case, scenario switch in Assumptions!B5).")
    st.caption(f"[Source code on GitHub]({REPO})")

inputs = Inputs(
    customers_per_day=s.customers, avg_bill=s.bill, fb_cost=s.fb / 100, rent_per_sqft=s.rent,
    area_sqft=s.area, seats=s.seats, deposit_months=s.deposit, fitout_rent_months=s.fitout,
    interiors_per_sqft=s.interiors, delivery_share=s.delivery_share / 100,
    delivery_commission=s.commission / 100, price_increase=s.price_inc / 100,
    cost_increase=s.cost_inc / 100, staff_salaries=s.salaries, overheads=s.overheads,
    working_capital_months=s.wc_months,
)
r = summary(inputs)
base = summary(Inputs())
is_base = inputs == Inputs()
adjusted = any(s[k] != v for k, v in preset_values(s.scenario).items()) or any(
    s[k] != DEFAULTS[k] for k in DEFAULTS if k not in LEVERS and k != "scenario")

# ------------------------------------------------------------------ header + verdict
st.title("☕ Café Break-Even Calculator")
st.caption(f"Kaapi Corner · HSR Layout, Bengaluru · {s.area:,} sq ft, {s.seats} seats · "
           f"scenario: **{s.scenario}{' (adjusted)' if adjusted else ''}** · amounts in ₹, excluding GST")

be, cust, inv, profit, pb = (r["break_even_per_day"], s.customers, r["investment"],
                             r["profit_full_capacity"], r["payback_month"])
if r["contribution"] <= 0:
    st.error("**Every sale loses money.** Ingredients, packaging and delivery commission cost more than the "
             "average bill. Raise prices or cut those costs.")
elif profit <= 0:
    st.error(f"**Loss-making.** The café needs **{be:.0f} customers a day** to cover its costs but expects "
             f"**{cust}**. At full capacity it loses **{inr(-profit)} a month**.")
elif pb is None:
    st.warning(f"**Profitable, but slow to pay back.** It breaks even at **{be:.0f} customers a day** "
               f"({cust} expected) but doesn't earn back the {lakh(inv)} investment within 3 years.")
else:
    st.success(f"**Viable.** It breaks even at **{be:.0f} customers a day** ({cust} expected) and earns back "
               f"the {lakh(inv)} investment in **month {pb}**.")

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Total investment", lakh(inv, 1), None if is_base else delta(inv, base["investment"], lambda d: f"₹{d / 1e5:.2f} lakh"),
          delta_color="inverse", help="Everything needed to open, including the refundable deposit and a cash reserve.")
k2.metric("Break-even", f"{per_day(be)} / day", None if is_base else delta(be, base["break_even_per_day"], lambda d: f"{d:.1f}"),
          delta_color="inverse", help="Customers needed every day to cover all monthly costs.")
k3.metric("Margin of safety", pct(r["margin_of_safety"]),
          None if is_base else delta(r["margin_of_safety"], base["margin_of_safety"], lambda d: f"{d * 100:.1f} pts"),
          help="How far footfall can fall below expectation before the café makes a loss.")
k4.metric("Monthly profit", inr(profit),
          None if is_base else delta(profit, base["profit_full_capacity"], inr),
          help="Operating profit at full capacity (from month 6), before depreciation, loan interest and income tax.")
k5.metric("Payback", payback_text(pb),
          None if (is_base or pb is None or base["payback_month"] is None)
          else delta(pb, base["payback_month"], lambda d: f"{d:.0f} months"),
          delta_color="inverse", help="First month when total operating profit has repaid the whole investment.")

tab_be, tab_cash, tab_start, tab_pnl, tab_sc, tab_about = st.tabs(
    ["Break-even", "Cash & payback", "Startup costs", "Monthly P&L", "Scenarios", "About & sources"])

# ------------------------------------------------------------------ Break-even
with tab_be:
    left, right = st.columns([3, 2], gap="large")
    with left:
        st.subheader("Sales vs total costs")
        top = int(min(400, max(60, (be if be != float("inf") else cust) * 1.8, cust * 1.4)))
        curve = break_even_curve(inputs, top).melt("Customers per day", var_name="Line", value_name="₹")
        curve["₹ lakh"] = curve["₹"] / 1e5
        domain = ["Sales", "Total costs", "Break-even", "Expected footfall"]
        colors = alt.Scale(domain=domain, range=[SALES, COSTS, LOSS, EXPECTED])
        lines = alt.Chart(curve).mark_line(strokeWidth=3).encode(
            x=alt.X("Customers per day:Q", title="Customers per day"),
            y=alt.Y("₹ lakh:Q", title="₹ lakh per month"),
            color=alt.Color("Line:N", scale=colors, legend=alt.Legend(orient="bottom", title=None)),
            tooltip=["Customers per day:Q", "Line:N", alt.Tooltip("₹ lakh:Q", format=".2f")],
        )
        marks = pd.DataFrame({"x": [be, cust], "Line": ["Break-even", "Expected footfall"]})
        marks = marks[marks["x"] != float("inf")]
        rules = alt.Chart(marks).mark_rule(strokeDash=[6, 4], strokeWidth=2).encode(
            x="x:Q", color=alt.Color("Line:N", scale=colors, legend=alt.Legend(orient="bottom", title=None)),
            tooltip=[alt.Tooltip("Line:N", title=""), alt.Tooltip("x:Q", title="Customers per day", format=".1f")],
        )
        st.altair_chart((lines + rules).properties(height=340))
        st.caption(f"The lines cross at break-even: **{per_day(be)} customers a day** "
                   f"({inr(r['break_even_sales'])} of sales a month). Every customer beyond that adds "
                   f"**{inr(r['contribution'], 2)}** of profit.")
    with right:
        st.subheader("One average bill")
        ue = unit_economics(inputs)
        ue["Share of bill"] = ue["Amount"] / inputs.avg_bill
        st.dataframe(pd.DataFrame({"": ue["Item"], "₹": ue["Amount"].map(lambda v: inr(v, 2)),
                                   "Share": ue["Share of bill"].map(pct)}), hide_index=True)
        st.subheader("Monthly fixed costs (year 1)")
        rent = inputs.area_sqft * inputs.rent_per_sqft
        fixed = pd.DataFrame({"": ["Rent", "Staff salaries", "Staff benefits & meals (10%)",
                                   "Utilities, marketing & other overheads", "Total fixed costs"],
                              "₹ per month": [rent, inputs.staff_salaries, inputs.staff_salaries * inputs.benefits,
                                              inputs.overheads, r["fixed_costs"]]})
        fixed["₹ per month"] = fixed["₹ per month"].map(inr)
        st.dataframe(fixed, hide_index=True)
        st.caption(f"Break-even = fixed costs ÷ contribution per customer = {inr(r['fixed_costs'])} ÷ "
                   f"{inr(r['contribution'], 2)} = {r['break_even_per_month']:,.0f} customers a month. "
                   f"That means each seat must be filled **{per_day(r['seat_turns'])} times a day**.")

    st.subheader("What moves break-even?")
    a, b = st.columns(2, gap="large")

    def be_day(i: Inputs) -> float:
        c = contribution_per_customer(i)
        return fixed_costs_year1(i) / c / i.open_days if c > 0 else None

    bills = range(max(100, s.bill - 150), s.bill + 151, 10)
    by_bill = pd.DataFrame({"Average bill (₹)": list(bills),
                            "Break-even customers per day": [be_day(replace(inputs, avg_bill=x)) for x in bills]})
    rents = range(max(40, s.rent - 80), s.rent + 81, 5)
    by_rent = pd.DataFrame({"Rent (₹ per sq ft)": list(rents),
                            "Break-even customers per day": [be_day(replace(inputs, rent_per_sqft=x)) for x in rents]})
    for col, df, xcol, note in (
        (a, by_bill, "Average bill (₹)", "A higher bill means fewer customers are needed."),
        (b, by_rent, "Rent (₹ per sq ft)", "Every ₹10 of rent per sq ft adds to the daily target."),
    ):
        with col:
            chart = alt.Chart(df.dropna()).mark_line(point=True, color=SALES).encode(
                x=alt.X(f"{xcol}:Q"), y=alt.Y("Break-even customers per day:Q"),
                tooltip=[f"{xcol}:Q", alt.Tooltip("Break-even customers per day:Q", format=".1f")])
            here = alt.Chart(pd.DataFrame({"x": [s.bill if "bill" in xcol else s.rent]})).mark_rule(
                strokeDash=[6, 4], color=COSTS).encode(x="x:Q")
            st.altair_chart((chart + here).properties(height=240))
            st.caption(note + " Dashed line = your current setting.")

# ------------------------------------------------------------------ Cash & payback
with tab_cash:
    pnl = r["pnl"].reset_index()
    pnl["Profit ₹ lakh"] = pnl["Operating profit"] / 1e5
    pnl["Cash ₹ lakh"] = pnl["Cash position"] / 1e5
    pnl["Result"] = pnl["Operating profit"].map(lambda v: "Profit" if v >= 0 else "Loss")
    c1, c2 = st.columns(2, gap="large")
    with c1:
        st.subheader("Operating profit each month")
        bars = alt.Chart(pnl).mark_bar().encode(
            x=alt.X("Month:O", title="Month", axis=alt.Axis(labelAngle=0, values=[1, 6, 12, 18, 24, 30, 36])),
            y=alt.Y("Profit ₹ lakh:Q", title="₹ lakh"),
            color=alt.Color("Result:N", scale=alt.Scale(domain=["Profit", "Loss"], range=[GAIN, LOSS]),
                            legend=alt.Legend(orient="bottom", title=None)),
            tooltip=["Month:O", alt.Tooltip("Profit ₹ lakh:Q", format=".2f")])
        st.altair_chart(bars.properties(height=300))
        st.caption("The first months lose money while regulars build up (40% of capacity in month 1, full by month 6). "
                   "Steps up each year come from 5% price rises.")
    with c2:
        st.subheader("Cash position after startup costs")
        line = alt.Chart(pnl).mark_line(strokeWidth=3, color=SALES, point=True).encode(
            x=alt.X("Month:Q", title="Month", scale=alt.Scale(domain=[1, MONTHS])),
            y=alt.Y("Cash ₹ lakh:Q", title="₹ lakh"),
            tooltip=["Month:Q", alt.Tooltip("Cash ₹ lakh:Q", format=".2f")])
        zero = alt.Chart(pd.DataFrame({"y": [0]})).mark_rule(color=COSTS).encode(y="y:Q")
        layers = line + zero
        if pb:
            layers += alt.Chart(pd.DataFrame({"x": [pb]})).mark_rule(strokeDash=[6, 4], color=GAIN).encode(x="x:Q")
        st.altair_chart(layers.properties(height=300))
        st.caption(f"Starts at −{lakh(inv)} (the investment) and adds each month's operating profit. "
                   + (f"It crosses zero in **month {pb}** — the payback point." if pb else
                      "It doesn't reach zero within 3 years."))
    st.subheader("Year by year")
    y = r["yearly"].reset_index()
    st.dataframe(pd.DataFrame({"Year": y["Year"].map(lambda v: f"Year {v}"), "Sales": y["Sales"].map(inr),
                               "Operating profit": y["Operating profit"].map(inr),
                               "Operating margin": y["Operating margin"].map(pct)}), hide_index=True)

# ------------------------------------------------------------------ Startup costs
with tab_start:
    sc = startup_costs(inputs)
    c1, c2 = st.columns([3, 2], gap="large")
    with c1:
        st.subheader(f"Total investment: {inr(inv)} ({lakh(inv)})")
        qty = [f"{q * 100:.0f}%" if "Contingency" in it else f"{q:,.0f}" for q, it in zip(sc["Quantity"], sc["Item"])]
        st.dataframe(pd.DataFrame({"Category": sc["Category"], "Item": sc["Item"], "Quantity": qty,
                                   "Rate": sc["Rate"].map(inr), "Cost": sc["Cost"].map(inr), "Basis": sc["Basis"]}),
                     hide_index=True, height=670)
    with c2:
        st.subheader("By category")
        cat = sc.groupby("Category", sort=False)["Cost"].sum().reset_index()
        cat["₹ lakh"] = cat["Cost"] / 1e5
        cat["Share"] = cat["Cost"] / inv
        bar = alt.Chart(cat).mark_bar(color=SALES).encode(
            y=alt.Y("Category:N", sort="-x", title=None), x=alt.X("₹ lakh:Q", title="₹ lakh"),
            tooltip=["Category:N", alt.Tooltip("₹ lakh:Q", format=".2f"), alt.Tooltip("Share:Q", format=".1%")])
        st.altair_chart(bar.properties(height=300))
        deposit = sc.loc[sc["Item"].str.startswith("Security deposit"), "Cost"].sum()
        st.caption(f"{inr(deposit)} of this is the refundable security deposit, and "
                   f"{inr(sc['Cost'].iloc[-1])} is a cash reserve for the slow first months.")

# ------------------------------------------------------------------ Monthly P&L
with tab_pnl:
    st.subheader("Monthly profit & loss — first 3 years")
    p = r["pnl"]
    shown = ["Customers per day", "Average bill", "Sales", "Total variable costs", "Gross profit", "Rent",
             "Staff salaries", "Staff benefits & meals", "Utilities, marketing & other overheads",
             "Total fixed costs", "Operating profit", "Operating margin", "Cash position"]
    table = pd.DataFrame(index=shown)
    for m in p.index:
        col = []
        for line in shown:
            v = p.at[m, line]
            col.append(f"{v:,.0f}" if line == "Customers per day" else pct(v) if line == "Operating margin" else inr(v))
        table[f"M{m}"] = col
    st.dataframe(table, height=500)
    st.caption("Amounts in ₹ excluding GST. Operating profit is before depreciation, loan interest and income tax.")
    st.download_button("Download the P&L as CSV", r["pnl"].to_csv().encode("utf-8"),
                       file_name="cafe_monthly_pnl.csv", mime="text/csv")

# ------------------------------------------------------------------ Scenarios
with tab_sc:
    st.subheader("Pessimistic vs base vs optimistic")
    st.caption("Each scenario changes only the four main levers (footfall, bill, ingredient cost, rent) and keeps "
               "your other settings.")
    cols = {}
    for name in PRESETS:
        i = with_preset(inputs, name)
        cols[name] = (i, summary(i))
    if any(s[k] != v for k, v in preset_values(s.scenario).items()):
        cols["Your settings"] = (inputs, r)
    rows = {
        "Customers per day": lambda i, x: f"{i.customers_per_day:,.0f}",
        "Average bill": lambda i, x: inr(i.avg_bill),
        "Ingredient cost": lambda i, x: pct(i.fb_cost),
        "Rent per sq ft": lambda i, x: inr(i.rent_per_sqft),
        "Total investment": lambda i, x: lakh(x["investment"]),
        "Break-even customers per day": lambda i, x: per_day(x["break_even_per_day"]),
        "Margin of safety": lambda i, x: pct(x["margin_of_safety"]),
        "Monthly profit at full capacity": lambda i, x: inr(x["profit_full_capacity"]),
        "Payback": lambda i, x: payback_text(x["payback_month"]),
    }
    st.dataframe(pd.DataFrame({name: [f(i, x) for f in rows.values()] for name, (i, x) in cols.items()},
                              index=list(rows)))
    prof = pd.DataFrame({"Scenario": list(cols), "₹ lakh": [x["profit_full_capacity"] / 1e5 for _, x in cols.values()]})
    prof["Result"] = prof["₹ lakh"].map(lambda v: "Profit" if v >= 0 else "Loss")
    chart = alt.Chart(prof).mark_bar().encode(
        x=alt.X("Scenario:N", sort=list(cols), title=None, axis=alt.Axis(labelAngle=0)),
        y=alt.Y("₹ lakh:Q", title="Monthly profit at full capacity (₹ lakh)"),
        color=alt.Color("Result:N", scale=alt.Scale(domain=["Profit", "Loss"], range=[GAIN, LOSS]), legend=None),
        tooltip=["Scenario:N", alt.Tooltip("₹ lakh:Q", format=".2f")])
    st.altair_chart(chart.properties(height=280))
    st.caption("Footfall is the deciding number: in the pessimistic case the café expects fewer customers than it "
               "needs to break even, so it loses money every month.")

# ------------------------------------------------------------------ About
with tab_about:
    c1, c2 = st.columns(2, gap="large")
    with c1:
        st.subheader("What this is")
        st.markdown(
            "A startup cost and break-even model for **Kaapi Corner**, a planned neighbourhood café in "
            "HSR Layout, Bengaluru. It answers three questions:\n\n"
            "1. How much money is needed to open?\n"
            "2. How many customers a day does it need to stop losing money?\n"
            "3. When does it earn back the investment?\n\n"
            "It is the web version of an Excel model with the same formulas — download it from the sidebar.")
        st.subheader("How it works")
        st.markdown(
            "- **Startup costs:** 18 items, each quantity × rate, plus a 5% contingency and a working capital reserve.\n"
            "- **Contribution per customer:** the bill minus ingredients, packaging, payment fees and the average "
            "delivery commission.\n"
            "- **Break-even:** monthly fixed costs ÷ contribution per customer ÷ open days.\n"
            "- **Monthly P&L:** customers ramp up 40% → 55% → 70% → 80% → 90% → 100% over the first six months; "
            "prices, rent and salaries rise 5% a year.\n"
            "- **Payback:** cash position starts at minus the investment and adds each month's profit; payback is "
            "the month it reaches zero.\n\n"
            "All amounts exclude GST: cafés charge 5% GST without input tax credit, and that money goes to the "
            "government. Profit is before depreciation, loan interest and income tax.")
        st.subheader("Limits")
        st.markdown("- Uses public benchmarks, not broker or supplier quotes.\n"
                    "- No seasonality, loan interest, depreciation or income tax.\n"
                    "- Rent varies street by street in Bengaluru.")
    with c2:
        st.subheader("Base-case staff (₹ per month)")
        st.dataframe(pd.DataFrame([(role, n, inr(sal), inr(n * sal), src) for role, n, sal, src in STAFF],
                                  columns=["Role", "People", "Salary each", "Monthly cost", "Source"]),
                     hide_index=True)
        st.subheader("Base-case overheads (₹ per month)")
        st.dataframe(pd.DataFrame([(item, inr(v)) for item, v in OVERHEADS], columns=["Item", "Monthly cost"]),
                     hide_index=True)
        st.subheader("Sources")
        st.markdown(
            "- Rent: [Address Advisors](https://addressadvisors.com/forum/commercial-rent-per-square-foot-in-bangalore) "
            "(HSR Layout ₹60–140 per sq ft), "
            "[One City Property listing](https://www.onecityproperty.com/properties/high-street-commercial-space-for-rent-on-jnc-road-koramangala)\n"
            "- Space, deposit & licences: [Petpooja calculator](https://blog.petpooja.com/free-tools/cafe-startup-cost-calculator-free/), "
            "[Petpooja licence guide](https://blog.petpooja.com/finance-compliance/cafe-license-fssai-registration-complete-guide/)\n"
            "- Startup & equipment cost: [Restroworks](https://www.restroworks.com/blog/?p=15772)\n"
            "- Salaries: [Apna](https://apna.co/job/bengaluru-bangalore/barista-440942640), "
            "[Indeed Bengaluru café jobs](https://in.indeed.com/Cafe-jobs-in-Bengaluru,-Karnataka)\n"
            "- Ingredient cost: [Kaapi Machines](https://kaapimachines.com/cafe-business-management-growth/), "
            "[Restaurant India](https://www.restaurantindia.in/article/cafe-profit-margin-in-india-what-to-realistically-expect.16906)\n"
            "- Average bill: [Rajiv Talreja](https://rajivtalreja.com/blog/cafe-vs-restaurant-business/)\n"
            "- GST: [Razorpay](https://razorpay.com/learn/gst-on-food-and-restaurants/)\n\n"
            "Researched November 2026. Figures without a source are assumptions.")
        st.caption(f"Built by Vamshith N · [GitHub]({REPO})")
