with source as (

    select * from {{ source('donki_raw', 'raw_cme_impacts') }}

),

renamed as (

    select
        enlil_link,
        location,
        strptime("arrivalTime", '%Y-%m-%dT%H:%MZ')   as arrival_time,
        "isGlancingBlow"                              as is_glancing_blow,
        "isMinorImpact"                               as is_minor_impact

    from source

)

select * from renamed