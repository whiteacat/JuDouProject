-- 回归测试数据清理（按依赖顺序，2026-09-14 整体回归后执行）
delete from notifications where content like '回归%';
delete from favorites where event_id >= 10;
delete from reviews where content like '回归评价%';
delete from group_restaurants where group_id = 4;
delete from event_members where event_id >= 10;
delete from group_events where id >= 10;
delete from group_members where group_id = 4;
delete from announcements where group_id = 4;
delete from groups where id = 4;
delete from feedbacks where content like '回归反馈%';
update users set signature = null, preferences = '{"food": []}'::jsonb where id = 1;
select 'groups' as t, count(*) from groups
union all select 'group_events', count(*) from group_events
union all select 'reviews', count(*) from reviews
union all select 'feedbacks', count(*) from feedbacks
union all select 'favorites', count(*) from favorites
union all select 'group_members', count(*) from group_members;
