import {createRoot} from "react-dom/client";
import React, {useEffect} from "react";

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
import {cilUser, cilChatBubble, cilBank, cilBookmark, cilLayers, cilFile, cilAppsSettings} from '@coreui/icons'


const stringToColor = (str) => {
    let hash = 0
    for (let i = 0; i < str.length; i++) {
        hash = str.charCodeAt(i) + ((hash << 5) - hash)
    }
    const hue = Math.abs(hash) % 360
    return `hsl(${hue}, 70%, 40%)`
}

function NavItem({value, href, permissions, icon, role}) {
    const permission = href.split("/").slice(-2).join(".").toLowerCase()
    const show = role === "admin" || permissions.includes(permission)
    return show &&
        <CNavItem href={href}>
            <CIcon customClassName="nav-icon" icon={icon}/> {value}
        </CNavItem>
}

function SidebarMenu({userName = 'User', onLogout, currentUser, userPermissions}) {
    const avatarColor = stringToColor(userName)
    const permissions = userPermissions.map(permission => {
        return permission.name
    })

    return (
        <CSidebar className="border-end" colorScheme="dark" style={{height: '100vh', position: 'relative'}}>
            <CSidebarHeader className="border-bottom">
                <CSidebarBrand style={{textDecoration: 'none', fontSize: '1.5rem'}}>
                    Chatbot Management
                </CSidebarBrand>
            </CSidebarHeader>

            <CSidebarNav>
                <CNavTitle>Administration</CNavTitle>
                <NavItem href={"/management/ViewModelUser/list"} icon={cilUser} role={currentUser.role.name}
                         permissions={permissions} value={"Users"}></NavItem>
                <NavItem href={"/management/ViewModelChat/list"} icon={cilChatBubble} role={currentUser.role.name}
                         permissions={permissions} value={"Chats"}></NavItem>
                <NavItem href={"/management/ViewModelRole/list"} icon={cilBank} role={currentUser.role.name}
                         permissions={permissions} value={"Roles"}></NavItem>
                <NavItem href={"/management/ViewModelPermission/list"} icon={cilBookmark} role={currentUser.role.name}
                         permissions={permissions} value={"Permissions"}></NavItem>
                <NavItem href={"/management/ViewModelDocument/list"} icon={cilFile} role={currentUser.role.name}
                         permissions={permissions} value={"Documents"}></NavItem>
                {/*<NavItem href={"/management/ViewModelJob/list"} icon={cilNotes} role={currentUser.role.name}*/}
                {/*         permissions={permissions} value={"Jobs"}></NavItem>*/}
                <NavItem href={"/management/ViewModelCollection/list"} icon={cilLayers}
                         role={currentUser.role.name}
                         permissions={permissions} value={"Collections"}></NavItem>
                <NavItem href={"/management/ViewModelChatbotConfiguration/"} icon={cilAppsSettings}
                         role={currentUser.role.name}
                         permissions={permissions} value={"Chatbot Configuration"}></NavItem>
            </CSidebarNav>
            <CSidebarHeader className="border-top">
                <div
                    style={{
                        bottom: '1rem',
                        width: '100%',
                    }}>
                    <CDropdown direction="dropup" style={{display: 'inline-block'}}>
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

const currentUser = JSON.parse(document.getElementById("current_user").innerText)
const permissions = JSON.parse(document.getElementById("permissions").innerText)
sidebar.render(<SidebarMenu userName={currentUser.name} onLogout={logout} currentUser={currentUser}
                            userPermissions={permissions}/>)
