import React, {useState} from "react";
import {
    CButton,
    CButtonGroup,
    CModal,
    CModalBody,
    CModalFooter,
    CModalHeader,
    CPagination,
    CPaginationItem
} from "@coreui/react";
import CIcon from "@coreui/icons-react";
import {cilCloudDownload, cilSearch, cilTrash} from "@coreui/icons";

export function ActionsColumn({
                                  item,
                                  hasDelete = false,
                                  onDelete = null,
                                  confirmDelete = false,
                                  confirmMessage = "Are you sure?",
                                  hasDownload = false,
                                  onDownload = null,
                                  hasShow = false,
                                  showComponent = null
                              }) {
    const [visibleConfirm, setVisibleConfirm] = useState(false)
    const [visibleShow, setVisibleShow] = useState(false)

    function retOnClickDelete() {
        if (confirmDelete) {
            return () => setVisibleConfirm(true)
        }
        return () => onDelete(item)
    }

    function onShow() {
        setVisibleShow(true)
    }

    return (
        <>
            <CButtonGroup>
                {hasShow &&
                    <CButton
                        color="secondary"
                        variant="outline"
                        style={{height: "25px", padding: "0px", width: "25px"}}
                        onClick={onShow}
                    >
                        <CIcon icon={cilSearch}/>
                    </CButton>
                }
                {hasDelete &&
                    <CButton
                        color="secondary"
                        variant="outline"
                        style={{height: "25px", padding: "0px", width: "25px"}}
                        onClick={retOnClickDelete()}
                    >
                        <CIcon icon={cilTrash} size="md"/>
                    </CButton>
                }
                {hasDownload &&
                    <CButton
                        color="secondary"
                        variant="outline"
                        style={{height: "25px", padding: "0px", width: "25px"}}
                        onClick={onDownload}
                    >
                        <CIcon icon={cilCloudDownload}/>
                    </CButton>
                }
            </CButtonGroup>

            <CModal visible={visibleConfirm} onClose={() => setVisibleConfirm(false)}>
                <CModalHeader>Delete Confirm</CModalHeader>
                <CModalBody>{confirmMessage}</CModalBody>
                <CModalFooter>
                    <CButton color="danger" onClick={() => {
                        onDelete(item)
                        setVisibleConfirm(false)
                    }}>Delete</CButton>
                    <CButton color="secondary" onClick={() => setVisibleConfirm(false)}>Cancel</CButton>
                </CModalFooter>
            </CModal>

            <CModal visible={visibleShow} onClose={() => setVisibleShow(false)} size="xl">
                <CModalHeader>Details</CModalHeader>
                <CModalBody>
                    {showComponent}
                </CModalBody>
                <CModalFooter>
                    <CButton color="secondary" onClick={() => setVisibleShow(false)}>Close</CButton>
                </CModalFooter>
            </CModal>
        </>
    )
}

export function Pagination({page, setPage, page_size, total, searchFunc}) {

    const num_of_page = Math.ceil(total / page_size)

    const prev = () => {
        setPage(page - 1)
        searchFunc(page - 1)
    }

    const next = () => {
        setPage(page + 1)
        searchFunc(page + 1)
    }

    return (
        <CPagination aria-label="Pagination">
            {page > 1 && (
                <CPaginationItem aria-label="Previous" onClick={prev}>
                    &laquo;
                </CPaginationItem>
            )}

            <CPaginationItem>
                {total > 0 && (page - 1) * page_size + 1 || 0} - {Math.min(page * page_size, total)} of {total}
            </CPaginationItem>

            {page < num_of_page && (
                <CPaginationItem aria-label="Next" onClick={next}>
                    &raquo;
                </CPaginationItem>
            )}
        </CPagination>
    )
}
