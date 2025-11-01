import {createRoot} from "react-dom/client";
import React, {useEffect, useState} from "react";
import {CButton, CButtonGroup, CCard, CCardBody, CCol, CContainer, CRow, CSpinner} from "@coreui/react";
import {CChartLine, CChartBar} from "@coreui/react-chartjs";


function parseDailyResponse(items) {
    // items: [{ date: "YYYY-MM-DD", count: number }, ...]
    const labels = items.map((i) => i.date);
    const data = items.map((i) => i.count);
    return {labels, data};
}

function parseMonthlyResponse(items) {
    // items: [{ month: "YYYY-MM", count: number }, ...]
    const labels = items.map((i) => i.month);
    const data = items.map((i) => i.count);
    return {labels, data};
}

function StatsChart({
                        description,
                        defaultMode = "daily", // "daily" | "monthly"
                        dailyDays = 30,
                        monthlyMonths = 12,
                        dailyEndpoint = "/management/ViewModelDashboard/number_of_messages_daily",
                        monthlyEndpoint = "/management/ViewModelDashboard/number_of_messages_monthly",
                    }) {
    const [mode, setMode] = useState(defaultMode);
    const [loading, setLoading] = useState(false);
    const [labels, setLabels] = useState([]);
    const [values, setValues] = useState([]);
    const [error, setError] = useState(null);

    async function fetchDaily() {
        setLoading(true);
        setError(null);
        try {
            const url = `${dailyEndpoint}?days=${encodeURIComponent(dailyDays)}`;
            const res = await fetch(url, {method: "GET"});
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const json = await res.json();
            if (json.status !== "success") throw new Error("API error");
            const {labels: l, data: d} = parseDailyResponse(json.data);
            setLabels(l);
            setValues(d);
        } catch (err) {
            console.error("fetchDaily error:", err);
            setError(err.message || "Error when fetch daily data");
            setLabels([]);
            setValues([]);
        } finally {
            setLoading(false);
        }
    }

    async function fetchMonthly() {
        setLoading(true);
        setError(null);
        try {
            const url = `${monthlyEndpoint}?months=${encodeURIComponent(monthlyMonths)}`;
            const res = await fetch(url, {method: "GET"});
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const json = await res.json();
            if (json.status !== "success") throw new Error("API error");
            const {labels: l, data: d} = parseMonthlyResponse(json.data);
            setLabels(l);
            setValues(d);
        } catch (err) {
            console.error("fetchMonthly error:", err);
            setError(err.message || "Error when fetch monthly data");
            setLabels([]);
            setValues([]);
        } finally {
            setLoading(false);
        }
    }

    useEffect(() => {
        let mounted = true;
        (async () => {
            if (!mounted) return;
            if (mode === "daily") await fetchDaily();
            else await fetchMonthly();
        })()
        return () => {
            mounted = false;
        }
    }, [mode, dailyDays, monthlyMonths, dailyEndpoint, monthlyEndpoint])

    const chartOptions = {
        maintainAspectRatio: false,
        plugins: {
            legend: {display: false},
            tooltip: {enabled: false},
        },
        interaction: {mode: null, intersect: false},
        hover: {mode: null},
        events: [],
        scales: {
            x: {grid: {display: false}},
            y: {beginAtZero: true, ticks: {precision: 0}},
        },
    };

    const lineData = {
        labels,
        datasets: [
            {
                label: "Messages",
                backgroundColor: "rgba(13,110,253,0.08)",
                borderColor: "rgba(13,110,253,1)",
                pointBackgroundColor: "rgba(13,110,253,1)",
                data: values,
                fill: true,
                tension: 0.3,
            },
        ],
    };

    const barData = {
        labels,
        datasets: [
            {
                label: "Messages",
                backgroundColor: "rgba(255,193,7,0.85)",
                borderColor: "rgba(255,193,7,1)",
                data: values,
            },
        ],
    };

    return (
        <CCard>
            <CCardBody>
                <CRow className="align-items-center mb-3">
                    <CCol>
                        <h5 className="mb-0">
                            {description} ({mode === "daily" ? "daily" : "monthly"})
                        </h5>
                    </CCol>
                    <CCol xs="auto">
                        <CButtonGroup>
                            <CButton size={"sm"} color={mode === "daily" ? "primary" : "secondary"}
                                     onClick={() => setMode("daily")}>
                                Daily
                            </CButton>
                            <CButton size={"sm"} color={mode === "monthly" ? "primary" : "secondary"}
                                     onClick={() => setMode("monthly")}>
                                Monthly
                            </CButton>
                        </CButtonGroup>
                    </CCol>
                </CRow>

                {loading ? (
                    <div style={{height: 350, display: "flex", alignItems: "center", justifyContent: "center"}}>
                        <CSpinner/>
                    </div>
                ) : labels.length === 0 ? (
                    <div style={{height: 350, display: "flex", alignItems: "center", justifyContent: "center"}}>
                        No data
                    </div>
                ) : mode === "daily" ? (
                    <div style={{height: 350}}>
                        <CChartLine data={lineData} options={chartOptions} height={300}/>
                    </div>
                ) : (
                    <div style={{height: 350}}>
                        <CChartBar data={barData} options={chartOptions} height={300}/>
                    </div>
                )}
            </CCardBody>
        </CCard>
    )
}

function DashboardCard({description, color, url}) {

    const [value, setValue] = useState(null)
    const [loading, setLoading] = useState(false)

    useEffect(() => {
        fetch(url)
            .then((res) => res.json())
            .then((json) => {
                if (json.status === "success") {
                    setValue(json.data);
                }
            })
            .catch((err) => console.error(`Error: ${description}`, err))
            .finally(() => setLoading(false));
    }, []);


    return (
        <>
            {loading && <CSpinner color="danger"/> ||
                <CCard className={`text-white bg-${color}`}>
                    <CCardBody className="pb-4 d-flex justify-content-between align-items-start">
                        <div>
                            <div className="fs-4 fw-semibold">
                                {value !== null && value || "--"}
                            </div>
                            <div>{description}</div>
                        </div>
                    </CCardBody>
                </CCard>
            }
        </>
    )
}

function App() {
    return (
        <CContainer fluid className="py-3">
            <CRow className="g-3">
                <CCol xs={12} sm={6} md={2}>
                    <DashboardCard description={"Total Chat sessions"} color={"primary"}
                                   url={"/management/ViewModelDashboard/number_of_chat_sessions"}></DashboardCard>
                </CCol>
                <CCol xs={12} sm={6} md={2}>
                    <DashboardCard description={"Total Messages"} color={"secondary"}
                                   url={"/management/ViewModelDashboard/number_of_messages"}></DashboardCard>
                </CCol>
                <CCol xs={12} sm={6} md={2}>
                    <DashboardCard description={"Total Messages Today"} color={"success"}
                                   url={"/management/ViewModelDashboard/number_of_messages_today"}></DashboardCard>
                </CCol>
                <CCol xs={12} sm={6} md={2}>
                    <DashboardCard description={"Total Sessions Today"} color={"danger"}
                                   url={"/management/ViewModelDashboard/number_of_chat_sessions_today"}></DashboardCard>
                </CCol>
                <CCol xs={12} sm={6} md={2}>
                    <DashboardCard description={"Active Users"} color={"warning"}
                                   url={"/management/ViewModelDashboard/number_of_active_users"}></DashboardCard>
                </CCol>
                <CCol xs={12} sm={6} md={2}>
                    <DashboardCard description={"Active Users Today"} color={"info"}
                                   url={"/management/ViewModelDashboard/number_of_distinct_users_with_messages_today"}></DashboardCard>
                </CCol>
            </CRow>
            <br/>
            <CRow>
                <CCol xs={12} sm={12} md={12}>
                    <StatsChart description={"Number of messages"} defaultMode="daily" dailyDays={30}
                                monthlyMonths={12}
                                dailyEndpoint="/management/ViewModelDashboard/number_of_messages_daily"
                                monthlyEndpoint="/management/ViewModelDashboard/number_of_messages_monthly"/>
                </CCol>
            </CRow>
            <br/>
            <CRow>
                <CCol xs={12} sm={12} md={12}>
                    <StatsChart description={"Number of chat sessions"} defaultMode="daily" dailyDays={30}
                                monthlyMonths={12}
                                dailyEndpoint="/management/ViewModelDashboard/number_of_chat_sessions_daily"
                                monthlyEndpoint="/management/ViewModelDashboard/number_of_chat_sessions_monthly"/>
                </CCol>
            </CRow>
        </CContainer>
    )
}

const container = document.getElementById("root_container")
const root = createRoot(container)
const model_data = document.getElementById("model").innerText
const model = JSON.parse(model_data)

root.render(<App model={model}/>)
