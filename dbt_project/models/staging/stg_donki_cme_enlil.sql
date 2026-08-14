with source as (

    select * from {{ source('donki_raw', 'raw_cme_enlil') }}

),

renamed as (

    select
        enlil_link,
        analysis_link,
        strptime("modelCompletionTime", '%Y-%m-%dT%H:%MZ')          as model_completion_time,
        au,
        strptime("estimatedShockArrivalTime", '%Y-%m-%dT%H:%MZ')    as estimated_shock_arrival_time,
        "estimatedDuration"                                          as estimated_duration,
        rmin_re,
        kp_18,
        kp_90,
        kp_135,
        kp_180,
        "isEarthGB"                                                  as is_earth_gb,
        "isEarthMinorImpact"                                         as is_earth_minor_impact

    from source

)

select * from renamed