import React from "react";

function Pagination({search_url, page, page_size, total, keyword}) {
    const num_of_page = Math.ceil(total / page_size)
    const search = (page_index) => {
        let url = `${search_url}?page=${page_index}&page_size=${page_size}`
        if (keyword !== null) {
            url = `${url}&keyword=${keyword}`
        }

        window.location.replace(url)
    }

    const prev = () => {
        search(page - 1)
    }

    const next = () => {
        search(page + 1)
    }

    return (
        <>
            <nav aria-label={"Pagination"}>
                <ul className={"pagination"}>
                    {page > 1 &&
                        <li className={"page-item"}>
                            <a className={"page-link"} href={"#"} aria-label={"Previous"} onClick={prev}>
                                <span aria-hidden={"true"}>&laquo;</span>
                            </a>
                        </li>
                    }

                    <li className={"page-item"}>
                        <a className={"page-link"}
                           href={"#"}>{(page - 1) * page_size + 1} - {Math.min(page * page_size, total)} of {total}</a>
                    </li>

                    {page < num_of_page &&
                        <li className={"page-item"}>
                            <a className={"page-link"} href={"#"} aria-label={"Next"} onClick={next}>
                                <span aria-hidden={"true"}>&raquo;</span>
                            </a>
                        </li>
                    }
                </ul>
            </nav>
        </>
    )
}

export {Pagination}