with source as (

    select * from {{ source('donki_raw', 'raw_flr') }}

),

renamed as (

    select
        "flrID"                                    as flr_id,
        catalog,
        strptime("beginTime", '%Y-%m-%dT%H:%MZ')    as begin_time,
        strptime("peakTime", '%Y-%m-%dT%H:%MZ')     as peak_time,
        strptime("endTime", '%Y-%m-%dT%H:%MZ')      as end_time,
        "classType"                                  as class_type,
        -- classType looks like "M2.3": split into letter class + numeric magnitude
        substr("classType", 1, 1)                    as flare_class,
        try_cast(substr("classType", 2) as double)   as flare_magnitude,
        "sourceLocation"                             as source_location,
        "activeRegionNum"                            as active_region_num,
        note,
        strptime("submissionTime", '%Y-%m-%dT%H:%MZ') as submission_time,
        "versionId"                                  as version_id,
        link,
        instruments,
        "linkedEvents"                                as linked_events,
        "sentNotifications"                           as sent_notifications

    from source

)

select * from renamed