import {createRoot} from "react-dom/client";
import React, {useEffect, useRef, useState} from "react";

import {
    CButton,
    CCard,
    CCardBody,
    CCardFooter,
    CCol,
    CContainer,
    CForm,
    CFormInput, CNavItem,
    CNavTitle,
    CRow,
    CSidebar,
    CSidebarBrand,
    CSidebarHeader,
    CSidebarNav,
    CSidebarToggler,
} from '@coreui/react'


function ChatFrame({chat_id, history_messages}) {

    const initialMessages = history_messages !== null && history_messages.map((x) => {
        if (x.sender === "bot") {
            return {text: x.message, from: "recv"}
        } else {
            return {text: x.message, from: "sent"}
        }
    }) || []

    const [message, setMessage] = useState('');
    const [messages, setMessages] = useState(initialMessages);
    const ws = useRef(null);

    useEffect(() => {
        const protocol = window.location.protocol === 'https:' ? 'wss://' : 'ws://'
        const host = window.location.host
        const wsUrl = `${protocol}${host}/ws`
        ws.current = new WebSocket(wsUrl)

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

            const data = {
                "chat_id": chat_id,
                "message": message.trim(),
            }

            if (ws.current && ws.current.readyState === WebSocket.OPEN) {
                ws.current.send(JSON.stringify(data))
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
                                    placeholder="Question..."
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

function Sidebar({sessions}) {
    return (
        <>
            <CSidebar className="border-end" colorScheme="dark" style={{height: '100vh'}}>
                <CSidebarHeader className="border-bottom">
                    <CSidebarBrand style={{textDecoration: 'none', fontSize: '1.5rem'}}>Westaco Chatbot</CSidebarBrand>
                </CSidebarHeader>
                <div className="px-3 py-2">
                    <a href="/new_chat" style={{textDecoration: 'none'}}>
                        <CButton color="primary" variant="outline" className="w-100">
                            New Conversation
                        </CButton>
                    </a>
                </div>
                <CSidebarNav>
                    <CNavTitle>Sessions</CNavTitle>
                    {
                        sessions.map((session, index) => (
                            <CNavItem key={`item_${index}`} href={`/chats/${session["uuid"]}`}>
                                {session["name"]}
                            </CNavItem>
                        ))
                    }

                </CSidebarNav>
                <CSidebarHeader className="border-top">
                    <CSidebarToggler/>
                </CSidebarHeader>
            </CSidebar>
        </>
    )
}

function App({model, sessions}) {
    return (
        <>
            <main className={"d-flex flex-nowrap"} style={{height: '100vh'}}>
                <div>
                    <Sidebar sessions={sessions}></Sidebar>
                </div>
                {
                    model.messages !== null &&
                    <ChatFrame chat_id={model.chat_id} history_messages={model.messages}></ChatFrame>
                }
            </main>
        </>
    )
}

const container = document.getElementById("root_container")
const root = createRoot(container)

const model_data = document.getElementById("model").innerText
const model = JSON.parse(model_data)

const sessions_data = document.getElementById("sessions").innerText
const sessions = JSON.parse(sessions_data)

root.render(<App model={model} sessions={sessions}/>)
