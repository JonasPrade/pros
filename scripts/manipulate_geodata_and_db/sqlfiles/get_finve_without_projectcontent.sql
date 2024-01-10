SELECT *
FROM finve as fv
LEFT JOIN finve_to_projectcontent as fvpc ON fv.id = fvpc.finve_id
WHERE fvpc.finve_id IS NULL;