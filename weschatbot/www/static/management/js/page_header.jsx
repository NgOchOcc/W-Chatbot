import {createRoot} from "react-dom/client";
import React from "react";
import {CHeader, CHeaderBrand} from "@coreui/react";

function PageHeader({title}) {
    return (
        <>
            <CHeader>
                <CHeaderBrand style={{paddingLeft: "15px"}}>{title}</CHeaderBrand>
            </CHeader>
        </>
    )
}

const container = document.getElementById("page_header")
const pageHeader = createRoot(container)
const model_data = document.getElementById("model").innerText
const model = JSON.parse(model_data)

const title = document.getElementById("title").innerText || model["title"] || "Westaco Chatbot Management"
pageHeader.render(<PageHeader title={title}/>)
