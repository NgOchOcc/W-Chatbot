import {createRoot} from "react-dom/client";
import React from "react";
import {
    CCard,
    CCardBody, CCardHeader,
    CTable,
    CTableBody,
    CTableDataCell,
    CTableHead,
    CTableHeaderCell,
    CTableRow
} from "@coreui/react";

function App({model}) {
    return (
        <>
            <CCard>
                <CCardHeader>
                    Active Users
                </CCardHeader>
                <CCardBody>
                    <CTable striped hover responsive small>
                        <CTableHead>
                            <CTableRow>
                                <CTableHeaderCell style={{width: "20%"}}>User id</CTableHeaderCell>
                                <CTableHeaderCell style={{width: "80%"}}>Last active time</CTableHeaderCell>
                            </CTableRow>
                        </CTableHead>
                        <CTableBody>
                            {model.map((item, index) => (
                                <CTableRow key={index}>
                                    <CTableDataCell style={{width: "20%"}}><span
                                        style={{fontSize: "0.9rem"}}>{item["user_id"]}</span></CTableDataCell>
                                    <CTableDataCell style={{width: "80%"}}><span
                                        style={{fontSize: "0.9rem"}}>{item["last_active"]}</span></CTableDataCell>
                                </CTableRow>
                            ))}
                        </CTableBody>
                    </CTable>
                </CCardBody>
            </CCard>
        </>
    )
}

const container = document.getElementById("root_container")
const root = createRoot(container)
const model_data = document.getElementById("model").innerText
const model = JSON.parse(model_data)

root.render(<App model={model}/>)
