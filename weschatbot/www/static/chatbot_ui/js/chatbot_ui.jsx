import {createRoot} from "react-dom/client"
import React, {useEffect, useRef, useState} from "react"
import ReactMarkdown from 'react-markdown'
import 'github-markdown-css/github-markdown.css'

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
    CFormTextarea,
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


function Header({userName, chatId, logoutUrl}) {

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

    const initial = userName.trim().charAt(0).toUpperCase()
    const bgColor = pickColorFromString(userName)

    const onLogout = () => {
        console.log("Click Logout")
        window.location.replace(logoutUrl)
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

function normalizeMarkdown(input) {
    if (!input || typeof input !== 'string') return '';

    let s = input.replace(/\r\n?/g, '\n').replace(/[ \t]+/g, ' ').trim();

    s = s.replace(/([^\n])\s+(#{1,6}\s)/g, '$1\n\n$2');

    s = s.replace(/([^\n])\s+(-{3,})/g, '$1\n\n$2')
        .replace(/(-{3,})([^\n])/g, '$1\n\n$2')

    s = s.replace(/([^\n])\s+(\d+\.\s)/g, '$1\n$2');

    s = s.replace(/([^\n])\s+(-\s)/g, '$1\n$2');
    s = s.replace(/([^\n])\n((?:-|\d+\.)\s)/g, '$1\n\n$2')
        .replace(/([^\n])\n(#{1,6}\s)/g, '$1\n\n$2');
    s = s.replace(/^(#{1,6} .+?)(?=\n(?!\n))/gm, '$1\n');
    s = s.replace(/\n{3,}/g, '\n\n');

    return s;
}

function BotMessageBox({msg, index}) {
    const baseMessageStyle = {
        padding: '10px 15px',
        borderRadius: '12px',
        marginBottom: '10px',
        display: 'inline-block',
        wordBreak: 'break-word',
        maxWidth: '100%',
    };

    const messageStyle = {
        ...baseMessageStyle,
        backgroundColor: 'transparent',
        alignSelf: 'flex-start'
    };

    return (
        <div key={index} style={messageStyle}>
            <ReactMarkdown>
                {normalizeMarkdown(msg.text)}
            </ReactMarkdown>
        </div>
    );
}


function SentMessageBox({msg, index}) {
    const baseMessageStyle = {
        padding: '10px 15px',
        borderRadius: '12px',
        marginBottom: '10px',
        display: 'inline-block',
        wordBreak: 'break-word',
        maxWidth: '80%',
    };

    const messageStyle = {
        ...baseMessageStyle,
        backgroundColor: msg.from === 'sent' ? 'rgba(176,200,243,0.84)' : 'rgba(243,222,171,0.84)',
        alignSelf: msg.from === 'sent' ? 'flex-end' : 'flex-start'
    };

    return (
        <div key={index} style={messageStyle}>
            <ReactMarkdown>
                {normalizeMarkdown(msg.text)}
            </ReactMarkdown>
        </div>
    );
}

function NormalMessageBox({msg, index}) {
    return (
        <>
            {msg.from === 'sent' ? <SentMessageBox msg={msg} index={index}></SentMessageBox> :
                <BotMessageBox msg={msg} index={index}></BotMessageBox>
            }
        </>
    )

}

function PlaceholderMessageBox({msg, index}) {
    return (
        <span style={{display: 'inline-block', animation: 'blink 2s infinite'}}>
          <span className="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
            <i>Thinking ...</i>
          <style>
            {`
              @keyframes blink {
                0% { opacity: 0.2; }
                50% { opacity: 1; }
                100% { opacity: 0.2; }
              }
            `}
          </style>
        </span>
    )
}

function MessageBox({msg, index}) {
    return (
        <>
            {msg.isPlaceholder && <PlaceholderMessageBox index={index} msg={msg}/> ||
                <NormalMessageBox index={index} msg={msg}/>}
        </>
    )
}

function ChatFrame({chat_id, history_messages, userName}) {
    const initialMessages = history_messages !== null && history_messages.map((x) => ({
        text: x.message,
        from: x.sender === "bot" ? "recv" : "sent"
    })) || [];

    const [message, setMessage] = useState('');
    const [messages, setMessages] = useState(initialMessages);
    const textareaRef = useRef(null);
    const bottomRef = useRef(null);


    useEffect(() => {
        if (bottomRef.current) {
            bottomRef.current.scrollIntoView({behavior: 'smooth'});
        }
    }, [messages]);


    const ws = useRef(null);

    useEffect(() => {
        const protocol = window.location.protocol === 'https:' ? 'wss://' : 'ws://';
        const host = window.location.host;
        const wsUrl = `${protocol}${host}/ws`;
        ws.current = new WebSocket(wsUrl);

        ws.current.onopen = () => {
            console.log('WebSocket connected');
        };

        ws.current.onmessage = (event) => {
            console.log('Received message', event.data);
            try {
                const message = JSON.parse(event.data).text;
                const incomingMessage = {text: message, from: "recv"};

                setMessages((prev) => {
                    const filtered = [...prev];
                    const lastIndex = filtered.length - 1;
                    if (lastIndex >= 0 && filtered[lastIndex].isPlaceholder) {
                        filtered.splice(lastIndex, 1);
                    }
                    return [...filtered, incomingMessage];
                });
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
        e.preventDefault();
        if (message.trim()) {
            const data = {
                chat_id: chat_id,
                message: message.trim(),
            };

            if (ws.current && ws.current.readyState === WebSocket.OPEN) {
                ws.current.send(JSON.stringify(data));
            }

            const outgoingMessage = {text: message, from: 'sent'};
            const placeholderMessage = {text: '...', from: 'recv', isPlaceholder: true};

            setMessages((prev) => [...prev, outgoingMessage, placeholderMessage]);
            setMessage('');

            if (textareaRef.current) {
                textareaRef.current.style.height = '70px';
            }
        }
    };

    return (
        <CRow className="h-90 justify-content-center">
            <CCol lg="6" md="10" sm="12">
                <CCard style={{height: '85vh', border: 'none', boxShadow: 'none'}}>

                    <CCardBody className="d-flex flex-column scroll-stable">
                        {messages.length > 0 ? (
                            <>
                                {messages.map((msg, index) => (
                                    <MessageBox key={index} index={index} msg={msg}/>
                                ))}
                                <div ref={bottomRef}/>
                            </>
                        ) : (
                            <div className="d-flex justify-content-center align-items-center" style={{height: '100%'}}>
                                <h3>Hi {userName.trim()}, what should we dive into today?</h3>
                            </div>
                        )}
                    </CCardBody>

                    <CCardFooter style={{border: 'none', background: 'transparent'}}>
                        <CForm onSubmit={handleSendMessage}>
                            <CFormTextarea
                                ref={textareaRef}
                                placeholder="Question..."
                                value={message}
                                onChange={(e) => {
                                    setMessage(e.target.value);
                                    const textarea = e.target;
                                    textarea.style.height = 'auto';
                                    const maxHeight = 6 * 24;
                                    textarea.style.height = `${Math.min(textarea.scrollHeight, maxHeight)}px`;
                                }}
                                rows={1}
                                style={{
                                    resize: 'none',
                                    overflow: 'hidden',
                                    minHeight: '70px',
                                    maxHeight: '144px',
                                    width: '100%',
                                    transition: 'height 0.2s ease',
                                    borderRadius: '12px'
                                }}
                                onKeyDown={(e) => {
                                    if (e.key === 'Enter' && !e.shiftKey) {
                                        e.preventDefault();
                                        handleSendMessage(e);
                                    }
                                }}
                            />
                            {/*<CButton type="submit" color="primary">*/}
                            {/*    <CIcon icon={cilPaperPlane}/>*/}
                            {/*</CButton>*/}

                            <div className="text-end mt-1" style={{fontSize: '0.85rem', color: '#6c757d'}}>
                                Shift+Enter to add new line, Enter to send the question
                            </div>
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
                    <CSidebarBrand style={{textDecoration: 'none'}}>
                        <div
                            style={{
                                display: 'flex',
                                alignItems: 'center',
                                fontSize: '1.2rem',
                                padding: '4px 15px',
                                borderRadius: '6px',
                                transition: 'background-color 0.3s',
                                cursor: 'pointer'
                            }}
                            onMouseEnter={e => (e.currentTarget.style.backgroundColor = 'rgba(184,184,184,0.11)')}
                            onMouseLeave={e => (e.currentTarget.style.backgroundColor = 'transparent')}
                        >
                            <img
                                src="/static/chatbot_ui/westaco_icon.png"
                                alt="Logo"
                                style={{height: '30px', marginRight: '10px', textDecoration: 'none'}}
                            />
                            <b>Chatbot</b>
                        </div>
                    </CSidebarBrand>

                </CSidebarHeader>
                <div className="px-3 py-2">
                    <a href="/new_chat" style={{textDecoration: 'none'}}>
                        <CButton color="primary" variant="outline" className="w-100">
                            New Conversation
                        </CButton>
                    </a>
                </div>
                <CSidebarNav className={"scroll-stable"}>
                    <CNavTitle>Sessions</CNavTitle>
                    {
                        sessions.map((session, index) => {
                            const trimmedName = session.name.length > 20
                                ? session.name.slice(0, 20) + '...'
                                : session.name;

                            return (<CNavItem
                                key={session.uuid}
                                className="nav-item-with-trash"
                                href={`/chats/${session.uuid}`}>
                                {trimmedName}
                                <span className="trash-icon"
                                      onClick={(e) => {
                                          e.preventDefault()
                                          deleteSession(session.uuid)
                                      }}>
                                    <i className="bi bi-trash"/>
                                  </span>
                            </CNavItem>)
                        })
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
                        <Header userName={username} chatId={model.chat_id} logoutUrl={"/logout"}></Header>
                    </CRow>
                    <br/>
                    {
                        model.messages !== null &&
                        <ChatFrame chat_id={model.chat_id} history_messages={model.messages}
                                   userName={username}></ChatFrame>
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
