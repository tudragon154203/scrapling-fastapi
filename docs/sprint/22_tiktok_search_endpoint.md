endpoint /tiktok/search

Request Schema:

query: một hoặc nhiều từ khóa, string hoặc array
numVideos: 50,
sortType: RELEVANCE // implement sau: "MOST_LIKE", "DATE_POSTED"
recencyDays: ENUM(All, 24h, 7 days, 30 days, 90 days, 180 days) // implement ALL trước mấy cái kia sau

Response Schema:
id
title
authorHandle
likeCount
uploadTime
webViewUrl
