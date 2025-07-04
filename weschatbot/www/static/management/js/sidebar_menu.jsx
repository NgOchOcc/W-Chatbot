import {createRoot} from "react-dom/client";
import React from "react";

import {
    CDropdown, CDropdownItem, CDropdownMenu, CDropdownToggle,
    CNavItem,
    CNavTitle,
    CSidebar,
    CSidebarBrand,
    CSidebarHeader,
    CSidebarNav,
} from '@coreui/react'

import CIcon from '@coreui/icons-react'
import {cilUser, cilChatBubble, cilBank, cilBookmark} from '@coreui/icons'


const stringToColor = (str) => {
    let hash = 0
    for (let i = 0; i < str.length; i++) {
        hash = str.charCodeAt(i) + ((hash << 5) - hash)
    }
    const hue = Math.abs(hash) % 360
    return `hsl(${hue}, 70%, 40%)`
}

function SidebarMenu({userName = 'User', onLogout}) {
    const avatarColor = stringToColor(userName)

    return (
        <CSidebar className="border-end" colorScheme="dark" style={{height: '100vh', position: 'relative'}}>
            <CSidebarHeader className="border-bottom">
                <CSidebarBrand style={{textDecoration: 'none', fontSize: '1.5rem'}}>
                    Chatbot Management
                </CSidebarBrand>
            </CSidebarHeader>

            <CSidebarNav>
                <CNavTitle>Administration</CNavTitle>
                <CNavItem href="/management/ViewModelUser/list">
                    <CIcon customClassName="nav-icon" icon={cilUser}/> Users
                </CNavItem>
                <CNavItem href="/management/ViewModelChat/list">
                    <CIcon customClassName="nav-icon" icon={cilChatBubble}/> Chat Sessions
                </CNavItem>
                <CNavItem href="/management/ViewModelRole/list">
                    <CIcon customClassName="nav-icon" icon={cilBank}/> Role
                </CNavItem>
                <CNavItem href="/management/ViewModelPermission/list">
                    <CIcon customClassName="nav-icon" icon={cilBookmark}/> Permissions
                </CNavItem>
            </CSidebarNav>
            <CSidebarHeader className="border-top">
                <div
                    style={{
                        bottom: '1rem',
                        width: '100%',
                    }}>
                    <CDropdown direction="up" style={{display: 'inline-block'}}>
                        <CDropdownToggle
                            caret={false}
                            className="d-inline-flex align-items-center p-0 border-0 bg-transparent"
                            style={{cursor: 'pointer'}}
                        >
                            <div
                                style={{
                                    backgroundColor: avatarColor,
                                    width: '40px',
                                    height: '40px',
                                    borderRadius: '50%',
                                    display: 'inline-flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                    color: '#fff',
                                    fontWeight: 'bold',
                                }}>
                                {userName.charAt(0).toUpperCase()}
                            </div>
                            <span style={{marginLeft: '0.5rem', color: '#fff'}}>{userName}</span>
                        </CDropdownToggle>
                        <CDropdownMenu>
                            <CDropdownItem onClick={onLogout || (() => console.log('Logout clicked'))}>
                                Logout
                            </CDropdownItem>
                        </CDropdownMenu>
                    </CDropdown>
                </div>
            </CSidebarHeader>
        </CSidebar>
    )
}

const logout = () => {
    window.location.replace('/management/logout')
}


const container = document.getElementById("sidebar_menu")
const sidebar = createRoot(container)

const current_user = JSON.parse(document.getElementById("current_user").innerText)
sidebar.render(<SidebarMenu userName={current_user.name} onLogout={logout}/>)
