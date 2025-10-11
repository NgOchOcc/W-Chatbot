import {createRoot} from "react-dom/client";
import React, {useState} from "react";
import {
    CButton,
    CCol, CDropdown, CDropdownItem, CDropdownMenu, CDropdownToggle,
    CForm,
    CFormInput,
    CInputGroup,
    CInputGroupText, CRow,
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


function App({model}) {
    const pagination = model["pagination"]
    const searchParams = model["search_params"]
    const data = model["query_results"]

    const [messageId, setMessageId] = useState(searchParams["message_id"] && searchParams["message_id"] || "")
    const [page, setPage] = useState(pagination["page"])
    const pageSize = pagination["page_size"]
    const [fromDate, setFromDate] = useState(searchParams["from_date"])
    const [toDate, setToDate] = useState(searchParams["to_date"])


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
                            <CDropdownItem onClick={() => console.log("Export CSV")}>Summary</CDropdownItem>
                            <CDropdownItem onClick={() => console.log("Refresh")}>Analytic Result</CDropdownItem>
                            <CDropdownItem onClick={() => console.log("Refresh")}>Quiz</CDropdownItem>
                        </CDropdownMenu>
                    </CDropdown>
                </CCol>
            </CRow>
            <br/>
            <div style={{maxHeight: "700px", overflowY: "auto"}}>
                <CTable striped hover responsive small bordered>
                    <CTableHead>
                        <CTableRow>
                            <CTableHeaderCell style={{width: "5%"}}>#</CTableHeaderCell>
                            <CTableHeaderCell>id</CTableHeaderCell>
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
                                <CTableDataCell style={{width: "5%"}}>
                                    <ActionsColumn item={item} hasDelete={true} confirmDelete={true}
                                                   onDelete={() => _}/>
                                </CTableDataCell>
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
