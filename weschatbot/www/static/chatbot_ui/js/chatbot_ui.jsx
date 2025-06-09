import {createRoot} from "react-dom/client";
import React, {useEffect, useRef, useState} from "react";

import {
    CBadge,
    CButton,
    CCard,
    CCardBody,
    CCardFooter,
    CCol,
    CContainer,
    CForm,
    CFormInput,
    CNavGroup,
    CNavItem,
    CNavTitle,
    CRow,
    CSidebar,
    CSidebarBrand,
    CSidebarHeader,
    CSidebarNav,
    CSidebarToggler,
} from '@coreui/react'

import CIcon from '@coreui/icons-react'
import {cilCloudDownload, cilLayers, cilPuzzle, cilSpeedometer} from '@coreui/icons'


function ChatFrame() {

    const [message, setMessage] = useState('');
    const [messages, setMessages] = useState([]);
    const ws = useRef(null);

    useEffect(() => {
        ws.current = new WebSocket('ws://localhost:8000/ws');

        ws.current.onopen = () => {
            console.log('WebSocket connected');
        };

        ws.current.onmessage = (event) => {
            console.log('Received message', event.data);
            try {
                console.log(JSON.parse(event.data));
                const message = JSON.parse(event.data).text;
                const incomingMessage = {text: message, from: "recv"};

                setMessages((prev) => [...prev, incomingMessage]);
            } catch (error) {
                console.error('Error parsing message:', error);
            }
        };

        ws.current.onclose = () => {
            console.log('WebSocket disconnected');
        };

        return () => {
            if (ws.current) ws.current.close();
        };
    }, []);

    const handleSendMessage = (e) => {
        e.preventDefault()
        if (message.trim()) {


            if (ws.current && ws.current.readyState === WebSocket.OPEN) {
                ws.current.send(message);
            }

            const outgoingMessage = {text: message, from: 'sent'}

            setMessages((prev) => [...prev, outgoingMessage])
            setMessage('')
        }
    };

    const baseMessageStyle = {
        padding: '10px 15px',
        borderRadius: '12px',
        marginBottom: '10px',
        display: 'inline-block',
        wordBreak: 'break-word',
        maxWidth: '80%',
    };

    return (
        <CContainer fluid className="vh-90" style={{paddingTop: '20px'}}>
            <CRow className="h-100 justify-content-center">
                <CCol lg="8" md="10" sm="12">
                    <CCard style={{height: '95vh'}}>
                        <CCardBody className="d-flex flex-column" style={{overflowY: 'auto'}}>
                            {messages.map((msg, index) => {
                                const messageStyle = {
                                    ...baseMessageStyle,
                                    backgroundColor: msg.from === 'sent' ? '#d1e7dd' : '#f1f1f1',
                                    alignSelf: msg.from === 'sent' ? 'flex-end' : 'flex-start',
                                };

                                return (
                                    <div key={index} style={messageStyle}>
                                        {msg.text}
                                    </div>
                                );
                            })}
                        </CCardBody>
                        <CCardFooter>
                            <CForm className="d-flex" onSubmit={handleSendMessage}>
                                <CFormInput
                                    placeholder="Nhập tin nhắn..."
                                    value={message}
                                    onChange={(e) => setMessage(e.target.value)}
                                />
                                <CButton type="submit" color="primary" className="ms-2">
                                    Send
                                </CButton>
                            </CForm>
                        </CCardFooter>
                    </CCard>
                </CCol>
            </CRow>
        </CContainer>
    )
}

function Sidebar() {
    return (
        <>
            <CSidebar className="border-end" colorScheme="dark" style={{height: '100vh'}}>
                <CSidebarHeader className="border-bottom">
                    <CSidebarBrand style={{textDecoration: 'none', fontSize: '1.5rem'}}>Westaco Chatbot</CSidebarBrand>
                </CSidebarHeader>
                <CSidebarNav>
                    <CNavTitle>Sessions</CNavTitle>
                    <CNavItem href="#">
                        <CIcon customClassName="nav-icon" icon={cilSpeedometer}/> Nav item
                    </CNavItem>
                    <CNavItem href="#">
                        <CIcon customClassName="nav-icon" icon={cilSpeedometer}/> With badge{' '}
                        <CBadge color="primary ms-auto">NEW</CBadge>
                    </CNavItem>
                    <CNavGroup
                        toggler={
                            <>
                                <CIcon customClassName="nav-icon" icon={cilPuzzle}/> Nav dropdown
                            </>
                        }
                    >
                        <CNavItem href="#">
            <span className="nav-icon">
              <span className="nav-icon-bullet"></span>
            </span>{' '}
                            Nav dropdown item
                        </CNavItem>
                        <CNavItem href="#">
            <span className="nav-icon">
              <span className="nav-icon-bullet"></span>
            </span>{' '}
                            Nav dropdown item
                        </CNavItem>
                    </CNavGroup>
                    <CNavItem href="https://coreui.io">
                        <CIcon customClassName="nav-icon" icon={cilCloudDownload}/> Download CoreUI
                    </CNavItem>
                    <CNavItem href="https://coreui.io/pro/">
                        <CIcon customClassName="nav-icon" icon={cilLayers}/> Try CoreUI PRO
                    </CNavItem>
                </CSidebarNav>
                <CSidebarHeader className="border-top">
                    <CSidebarToggler/>
                </CSidebarHeader>
            </CSidebar>
        </>
    )
}

function App() {
    return (
        <>
            <main className={"d-flex flex-nowrap"} style={{height: '100vh'}}>
                <div>
                    <Sidebar></Sidebar>
                </div>
                <ChatFrame></ChatFrame>
            </main>
        </>
    )
}

const container = document.getElementById("root_container")
const root = createRoot(container)

root.render(<App/>)
