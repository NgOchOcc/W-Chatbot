const path = require("path");
const webpack = require('webpack');

const CHATBOT_UI_JS_DIR = path.resolve(__dirname, './static/chatbot_ui/js');
const CHATBOT_UI_BUILD_DIR = path.resolve(__dirname, './static/chatbot_ui/dist');

const MANAGEMENT_JS_DIR = path.resolve(__dirname, './static/management/js');
const MANAGEMENT_BUILD_DIR = path.resolve(__dirname, './static/management/dist');


const commonConfig = {
    resolve: {
        extensions: ['.js', '.jsx']
    },
    module: {
        rules: [
            {
                test: /\.js$/,
                exclude: /node_modules/,
                use: ["babel-loader"]
            },
            {
                test: /\.jsx$/,
                exclude: /node_modules/,
                use: ["babel-loader"]
            },
            {
                test: /\.css$/,
                use: ["style-loader", "css-loader"]
            }
        ]
    },
    plugins: [],
}

const chatbotUIConfig = {
    ...commonConfig,
    entry: {
        index: [`${CHATBOT_UI_JS_DIR}/index.jsx`],
        chatbot_ui: [`${CHATBOT_UI_JS_DIR}/chatbot_ui.jsx`]
    },
    output: {
        path: CHATBOT_UI_BUILD_DIR,
        filename: '[name].js'
    }
};


const managementConfig = {
    ...commonConfig,
    entry: {
        index: [`${MANAGEMENT_JS_DIR}/index.jsx`],
        sidebar_menu: [`${MANAGEMENT_JS_DIR}/sidebar_menu.jsx`],
        list_view: [`${MANAGEMENT_JS_DIR}/list_view.jsx`],
        add_view: [`${MANAGEMENT_JS_DIR}/add_view.jsx`],
        detail_view: [`${MANAGEMENT_JS_DIR}/detail_view.jsx`],
        update_view: [`${MANAGEMENT_JS_DIR}/update_view.jsx`],
        delete_view: [`${MANAGEMENT_JS_DIR}/delete_view.jsx`],
        user_change_password: [`${MANAGEMENT_JS_DIR}/user_change_password.jsx`],
    },
    output: {
        path: MANAGEMENT_BUILD_DIR,
        filename: '[name].js'
    }
};

module.exports = [chatbotUIConfig, managementConfig];