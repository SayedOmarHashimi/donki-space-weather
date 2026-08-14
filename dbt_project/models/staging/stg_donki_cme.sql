with source as (

    select * from {{ source('donki_raw', 'raw_cme') }}

),

renamed as (

    select
        "activityID"                                     as cme_id,
        catalog,
        strptime("startTime", '%Y-%m-%dT%H:%MZ')          as start_time,
        instruments,
        "sourceLocation"                                  as source_location,
        "activeRegionNum"                                 as active_region_num,
        note,
        strptime("submissionTime", '%Y-%m-%dT%H:%MZ')     as submission_time,
        "versionId"                                       as version_id,
        link,
        "linkedEvents"                                    as linked_events,
        "sentNotifications"                                as sent_notifications

    from source

)

select * from renamed