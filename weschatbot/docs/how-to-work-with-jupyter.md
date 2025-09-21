# How to work on jupyter

## Access to jupyter

Jupyter url:
```shell
http://192.168.153.44:8000/
```

Access to jupyter through above url. Ask administrator for account.

## Workflow

### Clone project
Clone project at: https://git.westaco.com/ro.it.dev/westaco-chatbot.git

### Workflow
Please follow steps as below when you do a task.

1. Create an issue on gitlab https://git.westaco.com/ro.it.dev/westaco-chatbot/-/issues
2. Create a branch and PR for your issue on gitlab UI
3. Checkout your branch in step 2
    ```shell
    git fetch origin
    git checkout <your_branch_name>
    ```
4. Code or do something
5. Commit and push your code to gitlab
6. Add reviewers for your PR in step 2
7. Wait until your PR is merged

## Note
1. Don't commit binary files
2. Clear outputs of jupyter notebook before commit your code
3. Don't run any agent on 192.168.153.44 server
