with flares as (

    select
        flr_id                                             as event_id,
        'FLR'                                                as event_type,
        peak_time                                            as event_time,
        'Class ' || class_type || ' solar flare'             as description,
        flare_magnitude                                      as severity_score

    from {{ ref('stg_donki_flr') }}

),

cmes as (

    select
        cme_id                                               as event_id,
        'CME'                                                 as event_type,
        start_time                                            as event_time,
        'Coronal mass ejection' ||
            case when source_location != '' then ' from ' || source_location else '' end
                                                                as description,
        null                                                  as severity_score

    from {{ ref('stg_donki_cme') }}

),

storms as (

    select
        gst_id                                               as event_id,
        'GST'                                                 as event_type,
        start_time                                            as event_time,
        'Geomagnetic storm'                                   as description,
        null                                                  as severity_score

    from {{ ref('stg_donki_gst') }}

),

unioned as (

    select * from flares
    union all
    select * from cmes
    union all
    select * from storms

)

select * from unioned
order by event_time desc