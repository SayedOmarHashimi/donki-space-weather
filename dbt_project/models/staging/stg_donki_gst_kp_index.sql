with source as (

    select * from {{ source('donki_raw', 'raw_gst_kp_index') }}

),

renamed as (

    select
        kp_id,
        "gstID"                                            as gst_id,
        strptime("observedTime", '%Y-%m-%dT%H:%MZ')        as observed_time,
        "kpIndex"                                            as kp_index,
        source

    from source

)

select * from renamed