import {createRoot} from "react-dom/client";
import React, {useState} from "react";
import {CButton, CCardBody, CCol, CForm, CFormInput, CFormLabel, CRow} from "@coreui/react";
import {CSRFToken} from "./utils";

function AuthForm({csrf_token}) {

    return (
        <div
            className="d-flex justify-content-center align-items-center"
            style={{minHeight: '100vh', padding: '1rem'}}>
            <div style={{maxWidth: 400, width: '100%'}}>
                <CRow className="shadow">
                    <CCol md={12} className="bg-white">
                        <CCardBody className="p-5">
                            <h1 className="mb-4">Login</h1>
                            <CForm action="/management/login" method="post">
                                <CSRFToken csrf_token={csrf_token}></CSRFToken>
                                <div className="mb-3">
                                    <CFormLabel htmlFor="username">Username</CFormLabel>
                                    <CFormInput type="text" id="username" placeholder="Enter username"
                                                name={"username"}
                                                onChange={(e) => setUsername(e.target.value)}
                                                required/>
                                </div>
                                <div className="mb-3">
                                    <CFormLabel htmlFor="password">Password</CFormLabel>
                                    <CFormInput
                                        type="password"
                                        id="password"
                                        placeholder="Enter password"
                                        name="password"
                                        onChange={(e) => setPassword(e.target.value)}
                                    />
                                </div>
                                <CButton color="primary" className="w-100 mb-2" type={"submit"}>
                                    Login
                                </CButton>
                                <div className="text-center">
                                    <a href="/forgot-password">Forgot password?</a>
                                </div>
                            </CForm>
                        </CCardBody>
                    </CCol>
                </CRow>
            </div>
        </div>
    )
}

function App({csrf_token}) {
    return (
        <>
            <AuthForm csrf_token={csrf_token}/>
        </>
    )
}

const container = document.getElementById("root_container")
const root = createRoot(container)

const csrf_token = document.getElementById("csrf_token").innerText.trim()

root.render(<App csrf_token={csrf_token}/>)
