import {createRoot} from "react-dom/client";
import React, {useState} from "react";
import {
    CBadge, CButton, CButtonGroup,
    CCard,
    CCardBody,
    CCardHeader, CCollapse,
    CListGroup,
    CListGroupItem, CModal, CModalBody, CModalFooter, CModalHeader,
    CTable, CTableBody, CTableDataCell,
    CTableHead,
    CTableHeaderCell,
    CTableRow
} from "@coreui/react";
import CIcon from "@coreui/icons-react";
import {cilSearch, cilTrash} from "@coreui/icons";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeRaw from "rehype-raw";


function App({model}) {
    return (
        <>
            <ChatSessionView data={model}></ChatSessionView>
        </>
    )
}

function ActionColumn({item}) {

    const [visibleDetail, setVisibleDetail] = useState(false)

    return (
        <>
            <CButtonGroup>
                <CButton
                    color="secondary"
                    variant="outline"
                    style={{height: "25px", width: "25px", padding: 0}}
                    onClick={() => setVisibleDetail(true)}
                >
                    <CIcon icon={cilSearch} size="md"/>
                </CButton>
            </CButtonGroup>

            <CModal visible={visibleDetail} onClose={() => setVisibleDetail(false)} size="lg">
                <CModalHeader>Message Detail</CModalHeader>
                <CModalBody>
                    <p>
                        <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeRaw]}>
                            {item["content"]}
                        </ReactMarkdown>
                    </p>
                </CModalBody>
                <CModalFooter>
                    <CButton color="secondary" onClick={() => setVisibleDetail(false)}>Close</CButton>
                </CModalFooter>
            </CModal>
        </>
    )
}

function ListMessages({data}) {
    return (
        <>
            <div style={{marginBottom: "10px", overflowY: 'auto'}}>
                <CTable striped hover responsive>
                    <CTableHead>
                        <CTableRow>
                            <CTableHeaderCell>#</CTableHeaderCell>
                            <CTableHeaderCell>ID</CTableHeaderCell>
                            <CTableHeaderCell>Sender</CTableHeaderCell>
                            <CTableHeaderCell>Content</CTableHeaderCell>
                            <CTableHeaderCell>Modified date</CTableHeaderCell>
                        </CTableRow>
                    </CTableHead>
                    <CTableBody>
                        {data.messages.map((msg) => (
                            <CTableRow key={msg.id}>
                                <CTableDataCell>
                                    <ActionColumn item={msg}></ActionColumn>
                                </CTableDataCell>
                                <CTableDataCell>{msg.id}</CTableDataCell>
                                <CTableDataCell>
                                    <CBadge color={msg.sender === 'bot' ? 'danger' : 'success'} className="ms-2">
                                        {msg.sender}
                                    </CBadge>
                                </CTableDataCell>
                                <CTableDataCell>{msg.content}</CTableDataCell>
                                <CTableDataCell>{msg["modified_date"]}</CTableDataCell>
                            </CTableRow>
                        ))}
                    </CTableBody>
                </CTable>
            </div>
        </>
    )
}

function Overview({data}) {
    return (
        <>
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
            </CListGroup></>
    )
}

function ChatSessionView({data}) {
    const [visible, setVisible] = useState(false)

    return (
        <div style={{maxHeight: '100vh', height: "auto", display: 'flex', flexDirection: 'column'}}>
            <CCard className="flex-grow-1 d-flex flex-column">
                <CCardHeader>
                    Chat Session #{data.id}
                    <CButton
                        color="link"
                        size="sm"
                        className="float-end"
                        style={{textDecoration: 'none'}}
                        onClick={() => setVisible(!visible)}
                    >
                        {visible ? 'Hide Info' : 'Show Info'}
                    </CButton>
                </CCardHeader>

                <CCardBody className="flex-grow-1 d-flex flex-column">
                    <CCollapse visible={visible}>
                        <Overview data={data}></Overview>
                    </CCollapse>

                    <h5>Messages</h5>
                    <div style={{flexGrow: 1, overflowY: 'auto'}}>
                        <ListMessages data={data}/>
                    </div>
                </CCardBody>
            </CCard>
        </div>
    )
}

const container = document.getElementById("root_container")
const root = createRoot(container)
const model_data = document.getElementById("model").innerText
const model = JSON.parse(model_data)

root.render(<App model={model}/>)
