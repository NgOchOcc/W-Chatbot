import {createRoot} from "react-dom/client"
import React from "react"
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeRaw from 'rehype-raw'
import {CCard, CCardBody, CCol, CRow} from "@coreui/react"

function ConvertedDocumentContent({content}) {
    return (
        <>
            <CCard style={{maxHeight: "90vh", overflowY: "auto"}}>
                <CCardBody>
                    <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeRaw]}>
                        {content}
                    </ReactMarkdown>
                </CCardBody>
            </CCard>
        </>
    )
}


function App({model}) {
    return (
        <>
            <h4>Converted Document</h4>
            <CRow className="justify-content-start">
                <CCol lg={6} sm={12} md={12}>
                    <ConvertedDocumentContent content={model["converted_content"]}/>
                </CCol>
            </CRow>
        </>
    )
}


const container = document.getElementById("root_container")
const root = createRoot(container)
const model_data = document.getElementById("model").innerText
const model = JSON.parse(model_data)

root.render(<App model={model}/>)