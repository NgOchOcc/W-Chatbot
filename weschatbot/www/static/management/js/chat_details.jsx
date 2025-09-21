import {createRoot} from "react-dom/client";
import React from "react";
import {
    CBadge,
    CCard,
    CCardBody,
    CCardHeader,
    CListGroup,
    CListGroupItem,
    CTable, CTableBody, CTableDataCell,
    CTableHead,
    CTableHeaderCell,
    CTableRow
} from "@coreui/react";


function App({model}) {
    return (
        <>
            <h4>Chat details</h4>
            <ChatSessionView data={model}></ChatSessionView>
        </>
    )
}

function ChatSessionView({data}) {

    return (
        <CCard>
            <CCardHeader>Chat Session #{data.id}</CCardHeader>
            <CCardBody>
                <CListGroup className="mb-4">
                    <CListGroupItem>
                        <strong>Name:</strong> {data.name}
                    </CListGroupItem>
                    <CListGroupItem>
                        <strong>UUID:</strong> {data.uuid}
                    </CListGroupItem>
                    <CListGroupItem>
                        <strong>Modified Date:</strong> {data.modified_date}
                    </CListGroupItem>
                    <CListGroupItem>
                        <strong>User:</strong> {data.user.name}{' '}
                        <CBadge color={data.user.is_active ? 'success' : 'secondary'} className="ms-2">
                            {data.user.is_active ? 'Active' : 'Inactive'}
                        </CBadge>
                    </CListGroupItem>
                    <CListGroupItem>
                        <strong>Role:</strong> {data.user.role.name}
                    </CListGroupItem>
                </CListGroup>

                <h5>Messages</h5>
                <div style={{maxHeight: '500px', overflowY: 'auto'}}>
                    <CTable striped hover responsive>
                        <CTableHead>
                            <CTableRow>
                                <CTableHeaderCell>ID</CTableHeaderCell>
                                <CTableHeaderCell>Sender</CTableHeaderCell>
                                <CTableHeaderCell>Content</CTableHeaderCell>
                                <CTableHeaderCell>Modified date</CTableHeaderCell>
                            </CTableRow>
                        </CTableHead>
                        <CTableBody>
                            {data.messages.map((msg) => (
                                <CTableRow key={msg.id}>
                                    <CTableDataCell>{msg.id}</CTableDataCell>
                                    <CTableDataCell>
                                        <CBadge color={msg.sender === 'bot' ? 'danger' : 'success'} className="ms-2">
                                            {msg.sender}
                                        </CBadge>

                                    </CTableDataCell>
                                    <CTableDataCell>{msg.content}</CTableDataCell>
                                    <CTableDataCell>{msg.modified_date}</CTableDataCell>
                                </CTableRow>
                            ))}
                        </CTableBody>
                    </CTable>
                </div>
            </CCardBody>
        </CCard>
    )
}


const container = document.getElementById("root_container")
const root = createRoot(container)
const model_data = document.getElementById("model").innerText
const model = JSON.parse(model_data)

root.render(<App model={model}/>)
