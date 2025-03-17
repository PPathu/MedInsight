
--note 

with patient_sample_sepsis as (
select a.*, b.long_title from `physionet-data.mimiciv_3_1_hosp.diagnoses_icd` a left join 
`physionet-data.mimiciv_3_1_hosp.d_icd_diagnoses` b 
on a.icd_code = b.icd_code
where 1=1
and b.icd_code in ('J189','R6510','R570', 'M179','R6521','99591') --sepsis and others compare disease
and a.hadm_id in ( select hadm_id from `physionet-data.mimiciv_3_1_icu.chartevents`) --has charevent icu records.
and hadm_id not in (
    select hadm_id from `physionet-data.mimiciv_3_1_hosp.diagnoses_icd` --not to complicated, limited diagnosis numbers.
    where seq_num>9
)
and hadm_id in (
    select hadm_id from `physionet-data.mimiciv_note.discharge`  --has discharge notes records.
)
)

select * from `physionet-data.mimiciv_note.discharge`  --note
where hadm_id in (
    select hadm_id from patient_sample_sepsis
)


--lab and chartevent

with patient_sample_sepsis as (
select a.*, b.long_title from `physionet-data.mimiciv_3_1_hosp.diagnoses_icd` a left join 
`physionet-data.mimiciv_3_1_hosp.d_icd_diagnoses` b 
on a.icd_code = b.icd_code
where 1=1
and b.icd_code in ('J189','R6510','R570', 'M179','R6521','99591') --sepsis and others
and a.hadm_id in ( select hadm_id from `physionet-data.mimiciv_3_1_icu.chartevents`) --has charevent icu records.
and hadm_id not in (
    select hadm_id from `physionet-data.mimiciv_3_1_hosp.diagnoses_icd` --not to complicated, limited diagnosis numbers.
    where seq_num>9
)
and hadm_id in (
    select hadm_id from `physionet-data.mimiciv_note.discharge`  --has discharge notes records.
)
)


select "icu_chart" as type, subject_id, a.hadm_id,a.itemid, a.charttime, label, a.value, a.valueuom,"" as flag,category 
from `physionet-data.mimiciv_3_1_icu.chartevents` a left join 
`physionet-data.mimiciv_3_1_icu.d_items` b on a.itemid = b.itemid
where 1=1 
and a.hadm_id in  (
    select hadm_id from patient_sample_sepsis)
and a.itemid in (223761, 220210, 223900, 220050, 220052, 220046, 220047)

union all 

select "lab" as type, subject_id, hadm_id,a.itemid, a.charttime,b.label, a.value, a.valueuom, flag, b.category
from `physionet-data.mimiciv_3_1_hosp.labevents`  a left join  --lab
`physionet-data.mimiciv_3_1_hosp.d_labitems` b on a.itemid = b.itemid 
where hadm_id in (
    select hadm_id from patient_sample_sepsis)
and a.itemid in (50912, 50885, 51237, 51275 , 51265, 50813,50818, 51300, 51144 )