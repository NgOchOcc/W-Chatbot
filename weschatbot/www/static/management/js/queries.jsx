import {createRoot} from "react-dom/client";
import React, {useEffect, useState} from "react";

import remarkGfm from "remark-gfm";
import rehypeRaw from "rehype-raw";
import ReactMarkdown from "react-markdown";

import {
    CButton, CCard, CCardBody, CCardHeader,
    CCol, CDropdown, CDropdownItem, CDropdownMenu, CDropdownToggle,
    CForm,
    CFormInput,
    CInputGroup,
    CInputGroupText, CModal, CModalBody, CModalFooter, CModalHeader, CRow,
    CTable,
    CTableBody,
    CTableDataCell,
    CTableHead,
    CTableHeaderCell,
    CTableRow
} from "@coreui/react";
import {ActionsColumn, Pagination} from "./components";


function SearchBar({search, setSearch, fromDate, setFromDate, toDate, setToDate, searchFunc}) {
    const handleSearch = () => {
        searchFunc()
    }

    return (

        <CForm className="row gy-2 gx-3 align-items-center">
            <CCol xs="auto">
                <CFormInput id="messageIdInput" placeholder="message id" value={search}
                            onChange={(e) => setSearch(e.target.value)}/>
            </CCol>
            <CCol xs="auto">
                <CInputGroup>
                    <CInputGroupText>From</CInputGroupText>
                    <CFormInput
                        type="date"
                        value={fromDate}
                        onChange={(e) => setFromDate(e.target.value)}/>
                </CInputGroup>
            </CCol>
            <CCol xs="auto">
                <CInputGroup>
                    <CInputGroupText>To</CInputGroupText>
                    <CFormInput
                        type="date"
                        value={toDate}
                        onChange={(e) => setToDate(e.target.value)}/>
                </CInputGroup>
            </CCol>
            <CCol xs="auto">
                <CButton color="primary" onClick={handleSearch}>
                    Search
                </CButton>
            </CCol>
        </CForm>
    )
}

function QuestionList({questions}) {
    if (!questions || questions.length === 0) {
        return <p>No questions available.</p>
    }

    return (

        <CTable striped bordered responsive style={{fontSize: "0.9rem"}}>
            <CTableHead>
                <CTableRow>
                    <CTableHeaderCell>#</CTableHeaderCell>
                    <CTableHeaderCell>Text</CTableHeaderCell>
                    <CTableHeaderCell>Created Date</CTableHeaderCell>
                    <CTableHeaderCell>Message ID</CTableHeaderCell>
                    <CTableHeaderCell>Query ID</CTableHeaderCell>
                </CTableRow>
            </CTableHead>
            <CTableBody>
                {questions.map((q, index) => (
                    <CTableRow key={index}>
                        <CTableDataCell>{index + 1}</CTableDataCell>
                        <CTableDataCell>{q["text"]}</CTableDataCell>
                        <CTableDataCell>{q["created_date"]}</CTableDataCell>
                        <CTableDataCell>{q["message_id"]}</CTableDataCell>
                        <CTableDataCell>{q["query_id"]}</CTableDataCell>
                    </CTableRow>
                ))}
            </CTableBody>
        </CTable>
    )
}

function DetailQueryResultSummary({summary}) {
    if (!summary) return <p>No data available.</p>

    const {
        row_id, document_text, count, v_avg, v_min, v_max,
        first_seen, last_seen, query_ids, message_ids, questions
    } = summary

    return (
        <>
            <div style={{display: "flex", gap: "2rem", alignItems: "flex-start", maxHeight: "70vh"}}>
                <div style={{flex: 1}}>
                    <CCard style={{maxHeight: "70vh"}}>
                        <CCardHeader>General Info</CCardHeader>
                        <CCardBody style={{scrollBehavior: "smooth", overflowY: "auto"}}>
                            <p><strong>Row ID:</strong> {row_id}</p>
                            <p><strong>Count:</strong> {count}</p>
                            <p><strong>Average Score:</strong> {v_avg.toFixed(3)}</p>
                            <p><strong>Min Score:</strong> {v_min.toFixed(3)}</p>
                            <p><strong>Max Score:</strong> {v_max.toFixed(3)}</p>
                            <p><strong>First Seen:</strong> {first_seen}</p>
                            <p><strong>Last Seen:</strong> {last_seen}</p>
                            <p style={{whiteSpace: "normal", wordBreak: "break-word"}}>
                                <strong>Query IDs:</strong>{" "}
                                <span style={{whiteSpace: "normal", wordBreak: "break-word"}}>
                                    {query_ids.join(", ")}
                                </span>
                            </p>
                            <p style={{whiteSpace: "normal", wordBreak: "break-word"}}>
                                <strong>Message IDs:</strong>{" "}
                                <span style={{whiteSpace: "normal", wordBreak: "break-word"}}>
                                    {message_ids.join(", ")}
                                </span>
                            </p>
                            <p><strong>Document Text:</strong>
                                <CCard style={{padding: "1rem"}}>
                                    <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeRaw]}>
                                        {document_text}
                                    </ReactMarkdown>
                                </CCard>
                            </p>
                        </CCardBody>
                    </CCard>
                </div>

                <div style={{flex: 1}}>
                    <CCard style={{maxHeight: "70vh"}}>
                        <CCardHeader>Questions</CCardHeader>
                        <CCardBody style={{scrollBehavior: "smooth", overflowY: "auto"}}>
                            <QuestionList questions={questions}></QuestionList>
                        </CCardBody>
                    </CCard>
                </div>
            </div>
        </>
    )
}

function AnalyticPage({data}) {
    return (
        <>
            <p>
                <ReactMarkdown>
                    {data}
                </ReactMarkdown>
            </p>
        </>
    )
}

function SummaryPage({data}) {
    return (
        <>
            <CTable striped bordered responsive style={{fontSize: "0.9rem"}}>
                <CTableHead>
                    <CTableRow>
                        <CTableHeaderCell>#</CTableHeaderCell>
                        <CTableHeaderCell>row_id</CTableHeaderCell>
                        <CTableHeaderCell style={{width: '40vw'}}>text</CTableHeaderCell>
                        <CTableHeaderCell>count</CTableHeaderCell>
                        <CTableHeaderCell>avg</CTableHeaderCell>
                        <CTableHeaderCell>min</CTableHeaderCell>
                        <CTableHeaderCell>max</CTableHeaderCell>
                        <CTableHeaderCell>first_seen</CTableHeaderCell>
                        <CTableHeaderCell>last_seen</CTableHeaderCell>
                    </CTableRow>
                </CTableHead>
                <CTableBody>
                    {data.map((item, index) => (
                        <CTableRow key={index}>
                            <CTableDataCell><ActionsColumn hasShow={true}
                                                           showComponent={<DetailQueryResultSummary
                                                               summary={item}></DetailQueryResultSummary>}></ActionsColumn></CTableDataCell>
                            <CTableDataCell>{item["row_id"]}</CTableDataCell>
                            <CTableDataCell>{item["document_text"]}</CTableDataCell>
                            <CTableDataCell>{item["count"]}</CTableDataCell>
                            <CTableDataCell>{item["v_avg"].toFixed(3)}</CTableDataCell>
                            <CTableDataCell>{item["v_min"].toFixed(3)}</CTableDataCell>
                            <CTableDataCell>{item["v_max"].toFixed(3)}</CTableDataCell>
                            <CTableDataCell>{item["first_seen"]}</CTableDataCell>
                            <CTableDataCell>{item["last_seen"]}</CTableDataCell>
                        </CTableRow>
                    ))}
                </CTableBody>
            </CTable>
        </>
    )
}

function AnalyticModal({visible, setVisible, fromDate, toDate}) {

    const [loading, setLoading] = useState(false)
    const [data, setData] = useState("")

    useEffect(() => {
        if (visible) {
            setLoading(true)
            fetch(`/management/ViewModelQuery/analyze_query_results?from_date=${fromDate}&to_date=${toDate}`)
                .then(res => res.json())
                .then(data => {
                    if (data.status === "success") {
                        setData(data.data)
                    }
                })
                .catch(err => {
                    console.error("Error fetching summary:", err)
                })
                .finally(() => setLoading(false))
        }
    }, [visible])

    return (
        <CModal visible={visible} onClose={() => setVisible(false)} className="modal-fullscreen">
            <CModalHeader>Analytic</CModalHeader>
            <CModalBody className={"modal-scroll-body"}>
                {loading ? <p>Loading...</p> : <AnalyticPage data={data}/>}
            </CModalBody>
            <CModalFooter>
                <CButton color="secondary" onClick={() => setVisible(false)}>Close</CButton>
            </CModalFooter>
        </CModal>
    )
}

function SummaryModal({visible, setVisible, fromDate, toDate}) {
    const [summaryData, setSummaryData] = useState([])
    const [loading, setLoading] = useState(false)

    useEffect(() => {
        if (visible) {
            setLoading(true)
            fetch(`/management/ViewModelQuery/query_result_summary?from_date=${fromDate}&to_date=${toDate}`)
                .then(res => res.json())
                .then(data => {
                    if (data.status === "success") {
                        setSummaryData(data.data)
                    }
                })
                .catch(err => {
                    console.error("Error fetching summary:", err)
                })
                .finally(() => setLoading(false))
        }
    }, [visible])

    return (
        <CModal visible={visible} onClose={() => setVisible(false)} className="modal-fullscreen">
            <CModalHeader>Summary</CModalHeader>
            <CModalBody className={"modal-scroll-body"}>
                {loading ? <p>Loading...</p> : <SummaryPage data={summaryData}/>}
            </CModalBody>
            <CModalFooter>
                <CButton color="secondary" onClick={() => setVisible(false)}>Close</CButton>
            </CModalFooter>
        </CModal>
    )
}

function App({model}) {
    const pagination = model["pagination"]
    const searchParams = model["search_params"]
    const data = model["query_results"]

    const [messageId, setMessageId] = useState(searchParams["message_id"] && searchParams["message_id"] || "")
    const [page, setPage] = useState(pagination["page"])
    const pageSize = pagination["page_size"]
    const [fromDate, setFromDate] = useState(searchParams["from_date"])
    const [toDate, setToDate] = useState(searchParams["to_date"])

    const [summaryVisible, setSummaryVisible] = useState(false)
    const [analyzeVisible, setAnalyzeVisible] = useState(false)


    function search(pageNum) {
        const url = `/management/ViewModelQuery/list?page=${pageNum}&page_size=${pageSize}&from_date=${fromDate}&to_date=${toDate}&message_id=${messageId}`
        window.location.replace(url)

    }

    function searchFunc() {
        search(page)
    }

    function searchPaginationFunc(pageNum) {
        search(pageNum)
    }

    return (
        <>
            <CRow className="align-items-center">
                <CCol xs="8">
                    <SearchBar
                        search={messageId}
                        setSearch={setMessageId}
                        fromDate={fromDate}
                        toDate={toDate}
                        setFromDate={setFromDate}
                        setToDate={setToDate}
                        searchFunc={searchFunc}
                    />
                </CCol>
                <CCol xs="4" className="text-end">
                    <CDropdown>
                        <CDropdownToggle color="secondary">Actions</CDropdownToggle>
                        <CDropdownMenu>
                            <CDropdownItem onClick={() => setSummaryVisible(true)}>Summary</CDropdownItem>
                            <CDropdownItem onClick={() => setAnalyzeVisible(true)}>Analytic Result</CDropdownItem>
                        </CDropdownMenu>
                    </CDropdown>

                    {summaryVisible &&
                        <SummaryModal visible={summaryVisible} setVisible={setSummaryVisible} fromDate={fromDate}
                                      toDate={toDate}></SummaryModal>
                    }

                    {analyzeVisible &&
                        <AnalyticModal visible={analyzeVisible} setVisible={setAnalyzeVisible} fromDate={fromDate}
                                       toDate={toDate}></AnalyticModal>
                    }

                </CCol>
            </CRow>
            <br/>
            <div style={{maxHeight: "700px", overflowY: "auto"}}>
                <CTable striped hover responsive small bordered>
                    <CTableHead>
                        <CTableRow>
                            <CTableHeaderCell>q_id</CTableHeaderCell>
                            <CTableHeaderCell style={{width: "15%"}}>query</CTableHeaderCell>
                            <CTableHeaderCell>document_text</CTableHeaderCell>
                            <CTableHeaderCell>cosine_score</CTableHeaderCell>
                            <CTableHeaderCell>rank</CTableHeaderCell>
                            <CTableHeaderCell>msg_id</CTableHeaderCell>
                            <CTableHeaderCell>doc_id</CTableHeaderCell>
                            <CTableHeaderCell>cl_id</CTableHeaderCell>
                            <CTableHeaderCell>rw_id</CTableHeaderCell>
                        </CTableRow>
                    </CTableHead>
                    <CTableBody style={{fontSize: "0.9rem"}}>
                        {data.map((item, index) => (
                            <CTableRow key={index}>
                                <CTableDataCell><span>{item["id"]}</span></CTableDataCell>
                                <CTableDataCell><span>{item["message_content"]}</span></CTableDataCell>
                                <CTableDataCell><span>{item["document_text"]}</span></CTableDataCell>
                                <CTableDataCell><span>{item["cosine_score"]}</span></CTableDataCell>
                                <CTableDataCell><span>{item["rank"]}</span></CTableDataCell>
                                <CTableDataCell><span>{item["message_id"]}</span></CTableDataCell>
                                <CTableDataCell><span>{item["document_id"]}</span></CTableDataCell>
                                <CTableDataCell><span>{item["collection_id"]}</span></CTableDataCell>
                                <CTableDataCell><span>{item["row_id"]}</span></CTableDataCell>
                            </CTableRow>
                        ))}
                    </CTableBody>
                </CTable>
            </div>
            <br/>
            <Pagination page_size={pageSize} page={page} setPage={setPage} total={pagination["total"]}
                        searchFunc={searchPaginationFunc}></Pagination>
        </>
    )
}


const container = document.getElementById("root_container")
const root = createRoot(container)
const model_data = document.getElementById("model").innerText
const model = JSON.parse(model_data)

root.render(<App model={model}/>)
