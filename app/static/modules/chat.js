(function () {
  window.FGChat = Object.freeze({
    fetchUnread: (...args) => window.fetchUnread(...args),
    loadInbox: (...args) => window.loadInbox(...args),
    openCreateGroupModal: (...args) => window.openCreateGroupModal(...args),
    submitCreateGroup: (...args) => window.submitCreateGroup(...args),
    toggleRequests: (...args) => window.toggleRequests(...args),
    sendRequest: (...args) => window.sendRequest(...args),
    handleReq: (...args) => window.handleReq(...args),
    handleCommReq: (...args) => window.handleCommReq(...args),
    unfriend: (...args) => window.unfriend(...args),
    fetchChatMessages: (...args) => window.fetchChatMessages(...args),
    openChat: (...args) => window.openChat(...args),
    connectDmWS: (...args) => window.connectDmWS(...args),
    sendDM: (...args) => window.sendDM(...args),
    uploadDMImage: (...args) => window.uploadDMImage(...args),
  });
})();
