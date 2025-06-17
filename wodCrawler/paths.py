urls = {
    'base': 'https://www.crossfit.com',
    'workout': 'https://www.crossfit.com/workout'
}

xpaths = {
    'article' : '//*[@id="main"]/section[1]/div/div[2]/div[1]/div/div/article/div',
    'article_p1' : '//*[@id="main"]/section[1]/div/div[2]/div[1]/div/div/article/div/p[1]',
    'article_p2' : '//*[@id="main"]/section[1]/div/div[2]/div[1]/div/div/article/div/p[2]',
    'article_p3' : '//*[@id="main"]/section[1]/div/div[2]/div[1]/div/div/article/div/p[3]',
    'article_p4' : '//*[@id="main"]/section[1]/div/div[2]/div[1]/div/div/article/div/p[4]',
    'date' : '//*[@id="main"]/section[1]/div/div[1]/h2',
    'comments' : '//div[starts-with(@id, "comment-")]',
    'comment_athlete' : './div[1]/div[1]',
    'comment_content' : './div[2]'
    
}


# 1. 와드 이름, 와드, 세팅
# 2. 와드 이름, 와드
# 3. 와드, 세팅
# 4. 와드

# p1이 제목이다 -> p2 와드 스크래핑 -> p3가 세팅이다 -> p3 세팅 스크래핑
# p1이 제목이다 -> p2 와드 스크래핑 -> p3가 세팅이 아니다 -> 끝
# p1이 제목이 아니다 -> p1 와드 스크래핑 -> p2가 세팅이다 -> p2 세팅 스크래핑
# p1이 제목이 아니다  -> p1 와드 스크래핑 -> p2가 세팅이 아니다 -> 끝