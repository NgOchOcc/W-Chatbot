import {createRoot} from "react-dom/client";
import React, {useEffect, useRef, useState} from "react";

import {
    CAvatar,
    CButton,
    CCard,
    CCardBody,
    CCardFooter,
    CCol,
    CContainer,
    CDropdown,
    CDropdownItem,
    CDropdownMenu,
    CDropdownToggle,
    CForm,
    CFormInput,
    CHeader,
    CHeaderNav,
    CNavItem,
    CNavTitle,
    CRow,
    CSidebar,
    CSidebarBrand,
    CSidebarHeader,
    CSidebarNav,
    CSidebarToggler,
} from '@coreui/react'

const colors = [
    '#f44336',
    '#e91e63',
    '#9c27b0',
    '#3f51b5',
    '#2196f3',
    '#009688',
    '#4caf50',
    '#ff9800',
    '#795548',
]

function pickColorFromString(str) {
    let hash = 0
    for (let i = 0; i < str.length; i++) {
        hash = str.charCodeAt(i) + ((hash << 5) - hash)
    }
    const idx = Math.abs(hash) % colors.length
    return colors[idx]
}

function Header({userName, chatId}) {

    const initial = userName.trim().charAt(0).toUpperCase()
    const bgColor = pickColorFromString(userName)

    const onLogout = () => {
        console.log("Click Logout")
        window.location.replace("/logout")
    }

    return (
        <>
            <CHeader>
                <CContainer fluid className={"py-0"}>
                    <CCol className={"col-md-2"}></CCol>
                    <CCol className={"col-md-8"}>
                        <div className="text-center">
                            <small className="text-muted">Chat ID:</small>{' '}
                            <strong>{chatId}</strong>
                        </div>
                    </CCol>
                    <CCol className={"col-md-2 d-flex justify-content-end"}>
                        <CHeaderNav className="ms-auto">
                            <CDropdown variant="nav-item" className="py-0 px-2">
                                <CDropdownToggle placement="bottom-end" className="py-0"
                                                 style={{
                                                     height: '42px',
                                                     lineHeight: '32px',
                                                 }}>
                                    <CAvatar className={"py-1"}
                                             content={initial}
                                             style={{
                                                 backgroundColor: bgColor,
                                                 color: '#fff',
                                                 fontWeight: '600',
                                             }}
                                             size="md"
                                    >{initial}</CAvatar>
                                </CDropdownToggle>
                                <CDropdownMenu className="pt-0" placement="bottom-end">
                                    <CDropdownItem header tag="div" className="text-center py-2">
                                        Hello, {userName}
                                    </CDropdownItem>
                                    <CDropdownItem divider/>
                                    <CDropdownItem onClick={onLogout}>
                                        <i className="bi bi-box-arrow-right me-2"/> Logout
                                    </CDropdownItem>
                                </CDropdownMenu>
                            </CDropdown>
                        </CHeaderNav>
                    </CCol>
                </CContainer>
            </CHeader>
        </>
    )
}


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
        <CRow className="h-90 justify-content-center">
            <CCol lg="8" md="10" sm="12">
                <CCard style={{height: '85vh'}}>
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
    )
}

function Sidebar({sessions}) {
    const deleteSession = (chat_id) => {
        if (!window.confirm("Are you sure to delete this conversation?")) return

        fetch(`/chats/${chat_id}`, {method: 'DELETE'})
            .then((res) => {
                if (!res.ok) throw new Error("Error")
            })
            .then(() => alert("Success!"))
            .catch((err) => {
                alert("Error!")
            });
    }

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
                            <CNavItem
                                key={session.uuid}
                                className="nav-item-with-trash"
                                href={`/chats/${session.uuid}`}>
                                {session.name}
                                <span className="trash-icon"
                                      onClick={(e) => {
                                          e.preventDefault()       // chặn link
                                          deleteSession(session.uuid)
                                      }}>
                                    <i className="bi bi-trash"/>
                                  </span>
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

function App({model, sessions, username}) {
    return (
        <>
            <main className={"d-flex flex-nowrap"} style={{height: '100vh'}}>
                <div>
                    <Sidebar sessions={sessions}></Sidebar>
                </div>
                <CContainer fluid className="vh-90" style={{paddingTop: '10px'}}>
                    <CRow>
                        <Header userName={username} chatId={model.chat_id}></Header>
                    </CRow>
                    <br/>
                    {
                        model.messages !== null &&
                        <ChatFrame chat_id={model.chat_id} history_messages={model.messages}></ChatFrame>
                    }
                </CContainer>

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

const username = document.getElementById("username").innerText

root.render(<App model={model} sessions={sessions} username={username}/>)
