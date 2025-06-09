import {createRoot} from "react-dom/client";
import React from "react";

import {
    CNavItem,
    CNavTitle,
    CSidebar,
    CSidebarBrand,
    CSidebarHeader,
    CSidebarNav,
    CSidebarToggler,
} from '@coreui/react'

import CIcon from '@coreui/icons-react'
import {cilUser} from '@coreui/icons'


function SidebarMenu() {
    return (
        <CSidebar className="border-end" colorScheme="dark" style={{height: '100vh'}}>
            <CSidebarHeader className="border-bottom">
                <CSidebarBrand style={{textDecoration: 'none', fontSize: '1.5rem'}}>Chatbot Management</CSidebarBrand>
            </CSidebarHeader>
            <CSidebarNav>
                <CNavTitle>Administration</CNavTitle>
                <CNavItem href="/management/ViewModelUser/list">
                    <CIcon customClassName="nav-icon" icon={cilUser}/>
                    {' '}
                    Users
                </CNavItem>
            </CSidebarNav>
            <CSidebarHeader className="border-top">
                <CSidebarToggler/>
            </CSidebarHeader>
        </CSidebar>
    )
}


const container = document.getElementById("sidebar_menu")
const sidebar = createRoot(container)
sidebar.render(<SidebarMenu/>)
