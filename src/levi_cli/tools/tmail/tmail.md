Send a message to the past

This tool is provided to enable you to proactively manage the context. You can see some `user` messages with text `CHECKPOINT {checkpoint_id}` wrapped in `<system>` tags in the context. When you feel there is too much irrelevant information in the current context, you can send a T-Mail to revert the context to a previous checkpoint with a message containing only the useful information. When you send a T-Mail, you must specify an existing checkpoint ID from the before-mentioned messages.

Typical scenarios you may want to send a T-Mail:

- You read a file, found it very large and most of the content is not relevant to the current task. In this case you can send a T-Mail immediately to the checkpoint before you read the file and give your past self only the useful part.
- You searched the web, the result is large.
  - If you got what you need, you may send a T-Mail to the checkpoint before you searched the web and put only the useful result in the mail message.
  - If you did not get what you need, you may send a T-Mail to tell your past self to try another query.
- You wrote some code and it did not work as expected. You spent many struggling steps to fix it but the process is not relevant to the ultimate goal. In this case you can send a T-Mail to the checkpoint before you wrote the code and give your past self the fixed version of the code and tell yourself no need to write it again because you already wrote to the filesystem.

After a T-Mail is sent, the system will revert the current context to the specified checkpoint, after which, you will no longer see any messages which you can now see after that checkpoint. The message in the T-Mail will be appended to the end of the context. So, next time you will see all the messages before the checkpoint, plus the message in the T-Mail. You must make it very clear in the message, tell your past self what you have done/changed, what you have learned and any other information that may be useful, so that your past self can continue the task without confusion and will not repeat the steps you have already done.

You must understand that, the T-Mail you send here will not revert the filesystem or any external state. That means, you are basically folding the recent messages in your context into a single message, which can significantly reduce the waste of context window.

When sending a T-Mail, DO NOT explain to the user. The user do not care about this. Just explain to your past self.
