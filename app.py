# (Previous code above remains unchanged until figure creation)

# --- Create Plotly Subplots ---
fig = make_subplots(
    rows=5, cols=1, shared_xaxes=False,
    vertical_spacing=0.05,  # Reduced spacing
    subplot_titles=[
        "Dengue Cases",
        "Max Temperature (°C)",
        "Min Temperature (°C)",
        "Mean Relative Humidity (%)",
        "Rainfall (mm)"
    ]
)

# --- Add Traces ---
def add_trace(row, col, y, name, color, is_integer=False, tickformat=None):
    fig.add_trace(go.Scatter(
        x=week_dates,
        y=filtered[y],
        name=name,
        mode="lines+markers",
        marker=dict(size=4),
        line=dict(color=color)
    ), row=row, col=col)

    axis_name = f'yaxis{"" if row == 1 else row}'
    axis_config = dict(
        title=name,
        showgrid=True,
        zeroline=True,
        gridcolor='lightgray',
        tickfont=dict(color='black'),
    )
    if is_integer:
        axis_config["tickformat"] = ",d"
    elif tickformat:
        axis_config["tickformat"] = tickformat

    fig.update_layout({axis_name: axis_config})

# Dengue Cases
add_trace(1, 1, "dengue_cases", "Dengue Cases (Weekly Sum)", "crimson", is_integer=True)

# Highlight Dengue threshold weeks
highlight_weeks = filtered[filtered["meets_threshold"] == True]
for dt in highlight_weeks["week_start_date"].drop_duplicates():
    fig.add_vrect(
        x0=dt,
        x1=dt + timedelta(days=6),
        fillcolor="red",
        opacity=0.15,
        line_width=0,
        layer="below",
        row=1, col=1
    )

# Max Temperature
add_trace(2, 1, "temperature_2m_max", "Max Temperature (°C) (Weekly Max)", "orange")
highlight_max = filtered[filtered["temperature_2m_max"] <= 35]
for dt in highlight_max["week_start_date"].drop_duplicates():
    fig.add_vrect(
        x0=dt, x1=dt + timedelta(days=6),
        fillcolor="orange", opacity=0.1, line_width=0,
        layer="below", row=2, col=1
    )

# Min Temperature
add_trace(3, 1, "temperature_2m_min", "Min Temperature (°C) (Weekly Min)", "blue")
highlight_min = filtered[filtered["temperature_2m_min"] >= 18]
for dt in highlight_min["week_start_date"].drop_duplicates():
    fig.add_vrect(
        x0=dt, x1=dt + timedelta(days=6),
        fillcolor="blue", opacity=0.1, line_width=0,
        layer="below", row=3, col=1
    )

# Humidity
fig.add_trace(go.Scatter(
    x=week_dates,
    y=filtered["relative_humidity_2m_mean"],
    name="Mean Relative Humidity (%) (Weekly Mean)",
    mode="lines+markers",
    marker=dict(size=4),
    line=dict(color="green")
), row=4, col=1)

fig.update_layout({
    f'yaxis4': dict(
        title="Mean Relative Humidity (%) (Weekly Mean)",
        showgrid=True,
        zeroline=True,
        gridcolor='lightgray',
        tickfont=dict(color='black'),
        range=[0, 100]
    )
})

highlight_humidity = filtered[filtered["relative_humidity_2m_mean"] >= 60]
for dt in highlight_humidity["week_start_date"].drop_duplicates():
    fig.add_vrect(
        x0=dt, x1=dt + timedelta(days=6),
        fillcolor="green", opacity=0.1, line_width=0,
        layer="below", row=4, col=1
    )

# Rainfall (with fixed tick format to avoid scientific notation)
add_trace(5, 1, "rain_sum", "Rainfall (mm) (Weekly Sum)", "purple", is_integer=False, tickformat=".2f")

# Add x-axis label only to last chart with spacing
fig.update_xaxes(
    row=5, col=1,
    title_text="Week Start Date",
    title_font=dict(size=12),
    title_standoff=30  # Space between tick labels and axis label
)

# --- Layout Update ---
fig.update_layout(
    height=2100,
    width=3000,
    title_text=f"Weekly Dengue and Climate Trends — {selected_dt} district(s) / {selected_sdt} block(s)",
    showlegend=False,
    margin=dict(t=80, b=100),
    template=None,
    plot_bgcolor="white",
    paper_bgcolor="white",
    font=dict(color='black'),
    xaxis=dict(range=[x_start, x_end])
)

# --- Configure X-axis per subplot ---
for i in range(1, 6):
    fig.update_xaxes(
        row=i, col=1,
        tickangle=-45,
        tickformat="%d-%b-%y",
        tickfont=dict(size=10, color='black'),
        ticks="outside",
        showgrid=True,
        gridcolor='lightgray',
        dtick=604800000
    )

# --- Display Plot ---
st.plotly_chart(fig, use_container_width=True)

# --- Threshold Notes ---
st.markdown("""
**Note on Thresholds**:  
- **Dengue Cases**: Weeks shaded **red** indicate `meets_threshold = True`.  
- **Max Temperature (°C)**: Weeks shaded **orange** indicate values ≤ 35°C.  
- **Min Temperature (°C)**: Weeks shaded **blue** indicate values ≥ 18°C.  
- **Mean Relative Humidity (%)**: Weeks shaded **green** indicate values ≥ 60%.
""")
