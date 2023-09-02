SELECT pc.id, pc.name, pc.description, pc.reason_project, pc.superior_project_content_id from projects_contents pc
JOIN public.projectcontent_to_group ptg on pc.id = ptg.projectcontent_id
WHERE pc.id=30
GROUP BY pc.id